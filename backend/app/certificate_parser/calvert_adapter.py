"""Read Calvert certificate tables separately from the cover and licensing letter."""
from __future__ import annotations

import re
from datetime import datetime

from backend.app.certificate_parser.adapters import AdapterMatch
from backend.app.certificate_parser.format_profiles import evaluate_format_profiles
from backend.app.certificate_parser.generic_extractor import _parse_numeric
from backend.app.certificate_parser.measurement_units import dimension_value
from backend.app.domain.document import DocumentLayout, PageLayout, TextBlock

ELEMENTS = {"C", "Si", "Mn", "P", "S", "Al", "Cr", "Cu", "Mo", "N", "Ni", "Nb", "Ti", "B", "V", "Ca", "Sn"}
ELEMENT_OCR_ALIASES = {"SI": "Si", "AI": "Al"}

def _below(page: PageLayout, header: TextBlock, pattern: str, bottom: float) -> list[TextBlock]:
    return sorted((block for block in page.blocks
                   if header.bbox.bottom - 2 <= block.bbox.top < bottom
                   and max(header.bbox.x0, block.bbox.x0) < min(header.bbox.x1, block.bbox.x1)
                   and re.fullmatch(pattern, block.text.strip())), key=lambda block: block.bbox.top)


def _evidence(block: TextBlock, field: str) -> dict:
    return {"page": block.page_number, "field_path": field, "bbox": block.bbox.as_dict(),
            "source_text": block.text, "confidence": block.confidence}


class CalvertAdapter:
    name = "ARCELORMITTAL_CALVERT"

    def match(self, document: DocumentLayout) -> AdapterMatch:
        profile, score, signals = evaluate_format_profiles(document)
        return AdapterMatch(self.name, score if profile == self.name else 0.0, signals)

    def extract(self, document: DocumentLayout) -> dict:
        pages = [page for page in document.pages if any(block.text.strip() == "Mill Certificate" for block in page.blocks)
                 and any(block.text.strip() == "Certificate Number" for block in page.blocks)]
        certificate_numbers, dates, descriptions, suppliers = set(), set(), [], set()
        rows = []
        rows_by_certificate = {}
        for page in pages:
            page_numbers = set()
            page_rows = []
            for block in page.blocks:
                if block.text.strip() == "Certificate Number":
                    values = _below(page, block, r"\d+", block.bbox.bottom + page.height * .035)
                    certificate_numbers.update(value.text.strip() for value in values)
                    page_numbers.update(value.text.strip() for value in values)
                if block.text.strip() == "Date":
                    values = _below(page, block, r"\d{2}/\d{2}/\d{4}", block.bbox.bottom + page.height * .035)
                    dates.update(value.text.strip() for value in values)
                if re.fullmatch(r"ArcelorMittal Calvert LLC", block.text.strip(), re.I):
                    suppliers.add(block.text.strip())
                if re.search(r"\bCoil\b.*\bmm\b", block.text, re.I):
                    descriptions.append(block)
            chemical_title = next((block for block in page.blocks
                                   if "CHEMICAL COMPOSITION OF THE COIL" in block.text), None)
            if chemical_title is None:
                continue
            coil_header = next((block for block in page.blocks if block.text.strip() == "Coil"
                                and block.bbox.top < chemical_title.bbox.top), None)
            heat_header = next((block for block in page.blocks if block.text.strip() == "Heat"
                                and block.bbox.top < chemical_title.bbox.top), None)
            if coil_header is None or heat_header is None:
                raise ValueError("Calvert: no se identificaron las columnas de rollo y colada")
            coils = _below(page, coil_header, r"[A-Za-z0-9-]*\d[A-Za-z0-9-]*", chemical_title.bbox.top)
            heats = _below(page, heat_header, r"[A-Za-z0-9-]*\d[A-Za-z0-9-]*", chemical_title.bbox.top)
            for coil in coils:
                heat = min(heats, key=lambda block: abs(block.bbox.top - coil.bbox.top), default=None)
                if heat is None or abs(heat.bbox.top - coil.bbox.top) > page.height * .015:
                    raise ValueError("Calvert: rollo sin colada asociada")
                row = {"product_id": coil.text.strip(), "heat_no": heat.text.strip(), "length_raw": "COIL",
                       "chemistry": {}, "evidence": [_evidence(coil, "product_id"), _evidence(heat, "heat_no")]}
                for label, key in (("Net", "net_weight_kg"), ("Gross", "gross_weight_kg")):
                    header = next((block for block in page.blocks if block.text.strip() == label
                                   and block.bbox.top < chemical_title.bbox.top), None)
                    if header:
                        values = _below(page, header, r"[\d,.]+", chemical_title.bbox.top)
                        value = min(values, key=lambda block: abs(block.bbox.top - coil.bbox.top), default=None)
                        if value and abs(value.bbox.top - coil.bbox.top) < page.height * .015:
                            row["evidence"].append(_evidence(value, key))
                            # Calvert prints kg with three decimal places; malformed separators remain evidence.
                            if not re.fullmatch(r"(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d{3})?", value.text.strip()):
                                continue
                            if value.text.count(",") > 1 and "." not in value.text:
                                continue
                            row[key] = _parse_numeric(value.text)
                            if key == "net_weight_kg" or "weight_kg" not in row:
                                row["weight_kg"] = row[key]
                                row["weight_kind"] = "net" if key == "net_weight_kg" else "gross"
                                row["evidence"].append(_evidence(value, "weight_kg"))
                rows.append(row)
                page_rows.append(row)
            if len(page_numbers) != 1:
                raise ValueError("Calvert: número de certificado ambiguo")
            if page_rows:
                rows_by_certificate.setdefault(next(iter(page_numbers)), []).extend(page_rows)
                number_block = next(block for block in page.blocks if block.text.strip() == next(iter(page_numbers)))
                for row in page_rows:
                    row["evidence"].append(_evidence(number_block, "certificate_no"))
            chemistry_heats = [block for block in page.blocks if block.bbox.top > chemical_title.bbox.bottom
                               and block.text.strip() in {row["heat_no"] for row in rows}]
            for header in page.blocks:
                element = ELEMENT_OCR_ALIASES.get(header.text.strip(), header.text.strip())
                if header.bbox.top <= chemical_title.bbox.bottom or element not in ELEMENTS:
                    continue
                for value in _below(page, header, r"\d+(?:\.\d+)?", header.bbox.bottom + page.height * .03):
                    above = [block for block in chemistry_heats if block.bbox.top <= value.bbox.top + 2]
                    heat = max(above, key=lambda block: block.bbox.top, default=None)
                    if heat:
                        for row in page_rows:
                            if row["heat_no"] == heat.text.strip():
                                if element in row["chemistry"] and row["chemistry"][element] != value.text.strip():
                                    raise ValueError("Calvert: lecturas químicas contradictorias")
                                row["chemistry"][element] = value.text.strip()
                                row["evidence"].append(_evidence(value, f"composition_pct.{element}"))
            page_descriptions = [block for block in descriptions if block.page_number == page.page_number]
            if len(page_descriptions) == 1:
                detail = page_descriptions[0]
                spec = re.search(r"\bCoil\s+(.+?)\s*/\s*([\d.,]+)\s*mm\s*[Xx×]\s*([\d.,]+)\s*mm", detail.text)
                for row in page_rows:
                    if spec:
                        row["standard"] = spec[1].strip()
                        row["thickness_mm"] = dimension_value(spec[2], "mm")
                        row["width_mm"] = dimension_value(spec[3].replace(",", ""), "mm")
                        row["evidence"].extend(_evidence(detail, key) for key in ("standard", "thickness_mm", "width_mm"))
                    row["rolling"] = "hot" if re.search(r"Hot Roll", detail.text, re.I) else (
                        "cold" if re.search(r"Cold Roll Base", page.text, re.I) else None)
                    if "Pickled & Oiled" in detail.text:
                        row["condition"] = ["pickled", "oiled"]
                    if re.search(r"\bAluminize Coil\b", detail.text, re.I):
                        row["coating_metal"] = "Al"
        if certificate_numbers != set(rows_by_certificate) or not rows:
            raise ValueError("Calvert: certificado ambiguo o sin rollos")
        description = descriptions[0] if len({block.text for block in descriptions}) == 1 else None
        product_name = description.text if description else (
            "Aluminize Coil" if descriptions and all(re.match(r"Aluminize Coil\b", block.text, re.I)
                                                     for block in descriptions) else None)
        standards = {row.get("standard") for row in rows}
        standard = next(iter(standards)) if len(standards) == 1 else None
        for page in pages:
            if "TENSILE TEST" not in page.text:
                continue
            numbers = {value.text.strip() for header in page.blocks if header.text.strip() == "Certificate Number"
                       for value in _below(page, header, r"\d+", header.bbox.bottom + page.height * .035)}
            test_rows = rows_by_certificate.get(next(iter(numbers)), []) if len(numbers) == 1 else []
            # shortcut: unlabelled tests attach only to a single coil; require explicit IDs for multi-coil tests.
            for label, key, pattern in (("Yield", "yield_strength_mpa", r"[\d.]+\s*MPa"),
                                        ("Tensile", "tensile_strength_mpa", r"[\d.]+\s*MPa"),
                                        (r"% To[tl]al", "elongation_pct", r"[\d.]+"),
                                        ("Top Side", "coating_superior_g_m2", r"[\d.]+"),
                                        ("Bottom Side", "coating_inferior_g_m2", r"[\d.]+")):
                header = next((block for block in page.blocks if re.fullmatch(label, block.text.strip())), None)
                if header:
                    values = _below(page, header, pattern, header.bbox.bottom + page.height * .05)
                    if len(values) == 1 and len(test_rows) == 1:
                        test_rows[0][key] = _parse_numeric(values[0].text.replace("MPa", "").strip())
                        test_rows[0]["evidence"].append(_evidence(values[0], key))
        supplemental = [block for page in document.pages if page not in pages for block in page.blocks
                        if "Identification according to international standard" in block.text]
        for row in rows:
            row["evidence"].extend(_evidence(block, "supplemental_standard") for block in supplemental)
        date = next(iter(dates)) if len(dates) == 1 else None
        return {"document": {"source_name": document.file_name, "certificate_no": next(iter(certificate_numbers)) if len(certificate_numbers) == 1 else None,
                             "supplier": next(iter(suppliers)) if len(suppliers) == 1 else None,
                             "issue_date_raw": datetime.strptime(date, "%m/%d/%Y").date().isoformat() if date else None,
                             "product_name": product_name},
                "standard": standard,
                "chemistry_scales": {element: 0 for element in ELEMENTS}, "rows": rows}
