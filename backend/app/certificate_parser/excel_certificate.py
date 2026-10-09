"""Extract mill tables and specification letters with worksheet/cell evidence."""

from __future__ import annotations

from datetime import date, datetime
from hashlib import sha256
import math
from pathlib import Path
import re
import unicodedata
from typing import Any, Callable

from backend.app.certificate_parser.measurement_units import dimension_value
from backend.app.document_ingestion.excel_reader import read_workbook
from backend.app.infrastructure.ocr import OcrCancellationRequested

ELEMENTS = {element.upper(): element for element in (
    "C", "Si", "Mn", "P", "S", "Al", "Ti", "Cu", "Ni", "Cr", "Mo", "N", "B",
    "Co", "Pb", "Nb", "W", "V", "Zr", "Bi", "Se", "Te",
)}
ELEMENTS["AL"] = "Al_total"


def text(value: Any) -> str:
    return " ".join(unicodedata.normalize("NFKC", str(value) if value is not None else "").split())


def header_text(value: Any) -> str:
    return text(value).upper().replace(" (", "(")


def json_value(value: Any) -> Any:
    if value is not None and value.__class__.__name__ in {"ArrayFormula", "DataTableFormula"}:
        return {"formula_type": value.__class__.__name__, "reference": value.ref,
                "text": getattr(value, "text", None)}
    return value.isoformat() if isinstance(value, (date, datetime)) else value


def number(value: Any) -> float | None:
    if isinstance(value, bool) or value in (None, ""):
        return None
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def observation(cell, value: Any, unit: str | None = None, *, inherited: bool = False) -> dict[str, Any]:
    return {
        "raw_value": json_value(cell.value), "normalized_value": value, "unit": unit,
        "source_text": f"'{cell.parent.title}'!{cell.coordinate}: {cell.value}",
        "source_label": f"'{cell.parent.title}'!{cell.coordinate}",
        "inherited": inherited,
    }


def yield_bound(value: Any) -> dict[str, Any] | None:
    match = re.fullmatch(r"(<=|>=|<|>|≤|≥|≧|≦)?\s*(\d+(?:\.\d+)?)", text(value))
    if not match:
        return None
    operator = {"≤": "<=", "≥": ">=", "≧": ">=", "≦": "<="}.get(match[1], match[1] or "=")
    return {"operator": operator, "value": float(match[2]), "unit": "MPa"}


def _headers(sheet) -> tuple[int, dict[str, int]] | None:
    for row in sheet.iter_rows(min_row=1, max_row=min(sheet.max_row, 40)):
        headers: dict[str, int] = {}
        for cell in row:
            if cell.value is not None:
                headers.setdefault(header_text(cell.value), cell.column)
        if ("WIDTH" in headers or "WIDTH(MM)" in headers) and ("THICK" in headers or "THICK(MM)" in headers):
            return row[0].row, headers
        if "SPEC" in headers and "ALLOY OR NON-ALLOY" in headers and any("YIELD POINT" in key for key in headers):
            return row[0].row, headers
    return None


def _chemistry_columns(sheet, header_row: int, headers: dict[str, int]) -> tuple[list[tuple[int, str]], list[int]]:
    fixed: list[tuple[int, str]] = []
    dynamic: list[int] = []
    for cell in sheet[header_row]:
        label = text(cell.value)
        match = re.search(r"溶鋼分析[・\s]+([A-Za-z]+)[・\s]+実績値", label)
        if match and match[1].upper() in ELEMENTS:
            fixed.append((cell.column, ELEMENTS[match[1].upper()]))
        if "溶鋼分析" in label and "元素名" in label:
            dynamic.append(cell.column)
        if label.upper() in ELEMENTS:
            fixed.append((cell.column, ELEMENTS[label.upper()]))
    return fixed, dynamic


def _ambiguous_chemistry(sheet, header_row: int) -> bool:
    labels = [text(cell.value) for cell in sheet[header_row] if "溶鋼分析" in text(cell.value)]
    if len(labels) != len(set(labels)):
        return True
    for cell in sheet[header_row]:
        if "溶鋼分析" not in text(cell.value) or "有効桁" not in text(cell.value):
            continue
        for row in range(header_row + 1, min(sheet.max_row, header_row + 20) + 1):
            value = number(sheet.cell(row, cell.column).value)
            if value is not None and (not value.is_integer() or not 0 <= value <= 10):
                return True
    return False


def _kimitsu_chemistry_columns(sheet, header_row: int, headers: dict[str, int]):
    # This supplied mill layout stores precision first and percentage second despite its headers.
    if sheet.title != "KIMITSU(MILL CERT)" or not all(headers.get(label) == column for label, column in
            (("MILL NO", 1), ("HEAT NO.", 3), ("THICK(MM)", 4), ("WIDTH(MM)", 5))):
        return None
    labels = [text(cell.value) for cell in sheet[header_row]]
    expected = [f"溶鋼分析・{element}・{suffix}" for element in ("C", "Si", "Mn", "P", "S")
                for suffix in ("実績値", "有効桁")]
    if labels[6:16] != expected:
        return None
    columns = []
    column = 7
    while column < sheet.max_column:
        first = re.fullmatch(r"溶鋼分析・\s*([A-Za-z]+)・(実績値|有効桁)", labels[column - 1])
        second = re.fullmatch(r"溶鋼分析・\s*([A-Za-z]+)・有効桁", labels[column])
        if first and second and first[1].upper() == second[1].upper() and first[1].upper() in ELEMENTS:
            columns.append((column + 1, ELEMENTS[first[1].upper()]))
            column += 2
        else:
            column += 1
    return columns, []


def _product(sheet, row: int, headers: dict[str, int], chemistry_columns, ambiguous: bool, *, inverted: bool = False) -> dict[str, Any]:
    def cell_for(*labels: str):
        column = next((headers[label] for label in labels if label in headers), None)
        return sheet.cell(row, column) if column else None

    identifier = f"{sheet.title}!row-{row}"
    product: dict[str, Any] = {
        "product_id": identifier, "heat_no": None, "label_no": None, "source_format": "xlsx",
        "composition_pct": {}, "mechanical_properties": {}, "observations": {"composition_pct": {}},
        "evidence": [{"sheet": sheet.title, "row": row, "region": identifier}],
    }
    observations = product["observations"]
    for key, labels in {
        "heat_no": ("HEAT NO.", "HEAT NO", "HEAT NUMBER", "CAST NO", "CAST NO."),
        "label_no": ("COIL NO", "COIL NO."),
        "source_certificate_no": ("MILL NO",),
        "standard": ("SPEC(MILL CERTIFICATE)", "ORDERING SPEC", "SPEC"),
    }.items():
        cell = cell_for(*labels)
        if cell:
            value = (text(cell.value) or None) if cell.data_type != "f" else None
            product[key] = value
            observations[key] = observation(cell, value)
    for key, labels in {
        "width_mm": ("WIDTH(MM)", "WIDTH"), "thickness_mm": ("THICK(MM)", "THICK"),
    }.items():
        cell = cell_for(*labels)
        if cell:
            value = dimension_value(text(cell.value), "mm") if cell.value is not None else None
            product[key] = value if value is not None and value > 0 else None
            observations[key] = observation(cell, product[key], "mm")

    description_cell = cell_for("PRODUCTION NAME", "PRODUCT NAME")
    description = text(description_cell.value).upper() if description_cell and description_cell.data_type != "f" else ""
    product["form"] = "flat_rolled" if any(word in description for word in ("SHEET", "STRIP", "PLATE")) else None
    product["rolling"] = "hot" if "HOT ROLLED" in description or "HOT-ROLLED" in description else (
        "cold" if "COLD ROLLED" in description or "COLD-ROLLED" in description else None
    )
    length = cell_for("LENGTH", "LENGTH(MM)")
    coiled_by_length = length is not None and text(length.value).upper() in {"C", "COIL", "COILED", "ROLLO"}
    product["coiled"] = True if "COIL" in description or coiled_by_length else (False if "PLATE" in description else None)
    if description_cell:
        for key in ("form", "rolling", "coiled"):
            if product[key] is not None and not (key == "coiled" and coiled_by_length):
                observations[key] = observation(description_cell, product[key])
    if length:
        if coiled_by_length:
            observations["coiled"] = observation(length, True)
        # Zero is a workbook coil placeholder, never a physical zero length.
        value = number(length.value)
        product["length_m"] = value / 1000 if value is not None and value > 0 and not product["coiled"] else None
        observations["length_m"] = observation(length, product["length_m"], "m")
    weight = cell_for("COIL WEIGHT(MT)", "WEIGHT(KG)")
    if weight:
        value = number(weight.value)
        product["weight_kg"] = value * (1000 if "COIL WEIGHT(MT)" in headers else 1) if value is not None and value > 0 else None
        observations["weight_kg"] = observation(weight, product["weight_kg"], "kg")

    fixed, dynamic = chemistry_columns
    chemical_cells = [(sheet.cell(row, column), element) for column, element in fixed]
    for column in dynamic:
        element = ELEMENTS.get(text(sheet.cell(row, column).value).upper())
        if element:
            chemical_cells.append((sheet.cell(row, column + 1), element))
    seen: set[str] = set()
    for cell, element in chemical_cells:
        value = number(cell.value)
        if inverted:
            precision = number(sheet.cell(row, cell.column - 1).value)
            if precision is None:
                if value != 0:
                    value = None
            elif not precision.is_integer() or not 0 <= precision <= 10:
                value = None
        if ambiguous or value is None or not 0 <= value <= 100 or element in seen:
            value = None
        if element in seen:
            product["composition_pct"][element] = None
            continue
        seen.add(element)
        product["composition_pct"][element] = value
        observations["composition_pct"][element] = observation(cell, value, "%")
    # Source fractions and NICO are claims, never classification results.
    for key, labels in {"source_fraction": ("FRACCION",), "source_nico": ("NICO",)}.items():
        cell = cell_for(*labels)
        if cell:
            observations[key] = observation(cell, json_value(cell.value) if cell.data_type != "f" else None)
    for column, label in ((column, label) for label, column in headers.items() if label.startswith("引張・") and "実績値" in label):
        key = "yield_strength_mpa" if "降伏" in label or "耐力" in label else ("tensile_strength_mpa" if "強さ" in label else None)
        if key:
            cell = sheet.cell(row, column)
            unit = text(sheet.cell(row, column - 1).value).upper().replace("²", "2")
            value = number(cell.value) if unit in {"MPA", "N/MM2", "N/MM^2"} else None
            if value is not None and value <= 0:
                value = None
            product["mechanical_properties"][key] = value
            observations[f"mechanical_properties.{key}"] = observation(cell, value, "MPa" if value is not None else None)
    return product


def extract_excel(path: Path, *, page_callback: Callable[[int, int], None] | None = None,
                  cancel_check: Callable[[], bool] | None = None) -> dict[str, Any]:
    workbook = read_workbook(path)
    products: list[dict[str, Any]] = []
    support: list[dict[str, Any]] = []
    sheets: list[dict[str, Any]] = []
    reasons = ["Importación Excel: revisar identidades, unidades, química y posibles filas repetidas entre hojas antes de aprobar."]
    try:
        for index, sheet in enumerate(workbook, 1):
            if cancel_check and cancel_check():
                raise OcrCancellationRequested("Importación cancelada")
            detected = _headers(sheet)
            source_rows = []
            for row in sheet.iter_rows():
                if cancel_check and row[0].row % 100 == 0 and cancel_check():
                    raise OcrCancellationRequested("Importación cancelada")
                cells = {cell.coordinate: json_value(cell.value) for cell in row if cell.value is not None}
                if cells:
                    source_rows.append({"row": row[0].row, "cells": cells})
            sheets.append({"sheet": sheet.title, "rows": source_rows})
            if detected:
                header_row, headers = detected
                if "ALLOY OR NON-ALLOY" in headers:
                    merges = list(sheet.merged_cells.ranges)
                    def resolved_cell(row, column):
                        for region in merges:
                            if region.min_row <= row <= region.max_row and region.min_col <= column <= region.max_col:
                                return sheet.cell(region.min_row, region.min_col)
                        return sheet.cell(row, column)
                    yield_column = next(column for label, column in headers.items() if "YIELD POINT" in label)
                    for row in range(header_row + 1, sheet.max_row + 1):
                        spec = sheet.cell(row, headers["SPEC"])
                        if spec.value is None or spec.data_type == "f":
                            continue
                        alloy = resolved_cell(row, headers["ALLOY OR NON-ALLOY"])
                        strength = resolved_cell(row, yield_column)
                        # Bounds remain bounds; these are specification claims, not measured product chemistry.
                        support.append({"specification": observation(spec, text(spec.value)),
                                        "alloy_claim": observation(alloy, (text(alloy.value) or None) if alloy.data_type != "f" else None, inherited=alloy.row != row),
                                        "yield_strength": observation(strength, yield_bound(strength.value), inherited=strength.row != row)})
                else:
                    ambiguous = _ambiguous_chemistry(sheet, header_row)
                    if ambiguous:
                        reasons.append(f"{sheet.title}: encabezados químicos invertidos/repetidos; química sin normalizar hasta confirmar el significado de las columnas.")
                    columns = _chemistry_columns(sheet, header_row, headers)
                    kimitsu_columns = _kimitsu_chemistry_columns(sheet, header_row, headers)
                    if ambiguous and kimitsu_columns:
                        columns = kimitsu_columns
                        ambiguous = False
                        reasons[-1] = f"{sheet.title}: formato KIMITSU con encabezados invertidos/repetidos; porcentajes tomados de la segunda columna de cada par. Confirmar contra el certificado original antes de aprobar."
                    for row in range(header_row + 1, sheet.max_row + 1):
                        width_column = headers.get("WIDTH(MM)", headers.get("WIDTH"))
                        thickness_column = headers.get("THICK(MM)", headers.get("THICK"))
                        if sheet.cell(row, width_column).value is None and sheet.cell(row, thickness_column).value is None:
                            continue
                        products.append(_product(sheet, row, headers, columns, ambiguous,
                                                 inverted=bool(kimitsu_columns)))
            if page_callback:
                page_callback(index, len(workbook.worksheets))
    finally:
        workbook.close()
    ingestion = {"format": "xlsx", "sheets": sheets, "specification_records": support,
                 "formula_policy": "preserved_not_evaluated", "identity_policy": "worksheet_row_no_automatic_deduplication"}
    if not products:
        reasons.append("Documento de apoyo o estructura no reconocida: no se crearon productos ni se asignaron clasificaciones.")
    return {"status": "needs_review", "adapter": "xlsx_mill_tables",
            "document": {"file_name": path.name, "sha256": sha256(path.read_bytes()).hexdigest(),
                         "page_count": None, "ingestion": ingestion},
            "detection": {"kind": "mill_certificate" if products else ("supporting_document" if support else "unknown"), "confidence": 1.0 if products or support else 0.0,
                          "signals": ["xlsx", "worksheet_cell_provenance"]},
            "certificate": {"document": {}, "products": products, "validation": {"requires_review": True}},
            "reasons": reasons, "field_candidates": [], "table_candidates": []}
