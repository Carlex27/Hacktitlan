"""Deterministic generic certificate extractor for previously unseen mill certificate layouts."""

from __future__ import annotations

from dataclasses import dataclass
import logging
import re
from typing import Any

from backend.app.certificate_parser.mill_certificate import normalize_certificate
from backend.app.certificate_parser.vocabulary import (
    DITTO_TOKENS,
    METADATA_LABELS,
    match_column_semantic,
    normalize_term,
    detect_scale_exponent,
)
from backend.app.domain.document import DocumentLayout, TableRegion
from backend.app.certificate_parser.layout_rows import recover_rows
from backend.app.certificate_parser.measurement_units import dimension_unit, dimension_value

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ColumnDefinition:
    index: int
    category: str  # "product_id", "heat_no", "dimension", "chemistry", "mechanical", "unknown"
    canonical_key: str | None
    exponent: int | None = None
    header: str = ""


@dataclass(frozen=True)
class GenericExtractionResult:
    is_valid_certificate: bool
    certificate: dict[str, Any] | None
    unmapped_blocks: list[dict[str, Any]]
    signals: list[str]
    reasons: list[str]


def _clean_cell(val: Any) -> str:
    if val is None:
        return ""
    return str(val).strip()


def _is_ditto(text: str) -> bool:
    clean = text.strip()
    return clean in DITTO_TOKENS


def _parse_numeric(value: str) -> float | None:
    clean = value.strip().replace(" ", "")
    if "," in clean and "." in clean:
        decimal_separator = "," if clean.rfind(",") > clean.rfind(".") else "."
        thousands_separator = "." if decimal_separator == "," else ","
        clean = clean.replace(thousands_separator, "").replace(decimal_separator, ".")
    elif "," in clean:
        integer, decimal = clean.rsplit(",", maxsplit=1)
        clean = clean.replace(",", "") if len(decimal) == 3 else f"{integer}.{decimal}"
    try:
        return float(clean)
    except ValueError:
        return None


class GenericCertificateExtractor:
    """Extracts products, chemistry, and dimensions from unknown layouts without ML hallucinations."""

    def extract(self, document: DocumentLayout) -> GenericExtractionResult:
        metadata = self._extract_metadata(document)
        signals: list[str] = [f"meta:{k}" for k in metadata if metadata[k]]

        tables_data = self._extract_tables_and_products(document)
        product_rows = tables_data["rows"]
        unmapped_blocks = self._collect_unmapped(document, tables_data["mapped_cell_indices"])

        if not product_rows:
            return GenericExtractionResult(
                is_valid_certificate=False,
                certificate=None,
                unmapped_blocks=unmapped_blocks,
                signals=signals,
                reasons=["No se pudieron segmentar filas válidas de productos o coladas"],
            )

        # Assemble intermediate raw payload for canonical normalization
        raw_payload: dict[str, Any] = {
            "document": {
                "source_name": document.file_name,
                "certificate_no": metadata.get("certificate_no"),
                "supplier": metadata.get("supplier"),
                "customer": metadata.get("customer"),
                "issue_date_raw": metadata.get("issue_date"),
                "shipping_date_raw": metadata.get("shipping_date"),
                "delivery_date_raw": metadata.get("delivery_date"),
                "product_name": metadata.get("product_name"),
                "field_evidence": metadata.get("field_evidence", {}),
            },
            "standard": metadata.get("standard"),
            "chemistry_scales": tables_data.get("chemistry_scales", {}),
            "rows": product_rows,
            "unmapped_blocks": unmapped_blocks,
        }
        corpus = normalize_term(document.text).replace(" ", "")
        cold = "coldrolled" in corpus or "冷轧" in corpus
        hot = "hotrolled" in corpus or "热轧" in corpus
        raw_payload["rolling"] = "cold" if cold and not hot else "hot" if hot and not cold else None
        if "egcoil" in corpus and "zn" in corpus:
            raw_payload["coating"] = {"metal": "Zn", "process": "electrolytic"}

        try:
            previous = {}
            previous_chemistry = {}
            previous_heat = None
            previous_scope = None
            for row in product_rows:
                if row.get("table_scope") != previous_scope:
                    previous = {}
                    previous_chemistry = {}
                    previous_heat = None
                previous_scope = row.get("table_scope")
                for key in ("heat_no", "thickness_mm", "width_mm", "length_raw"):
                    value = row.get(key)
                    if _is_ditto(str(value)):
                        if previous.get(key) is None:
                            row[key] = None
                        else:
                            value = previous[key]
                    previous[key] = value if row.get(key) is not None else None
                current_heat = previous.get("heat_no")
                if current_heat is None or current_heat != previous_heat:
                    previous_chemistry = {}
                for element, value in list(row.get("chemistry", {}).items()):
                    if _is_ditto(str(value)) and previous_chemistry.get(element) is None:
                        del row["chemistry"][element]
                    elif not _is_ditto(str(value)):
                        previous_chemistry[element] = value
                previous_chemistry = {element: previous_chemistry.get(element) for element in row.get("chemistry", {})}
                previous_heat = current_heat
            normalized = normalize_certificate(raw_payload)
            for product, row in zip(normalized["products"], product_rows):
                product["raw_values"] = row.get("raw_values", {})
                for field, detail in product["observations"].items():
                    if field == "composition_pct":
                        for element, chemical_detail in detail.items():
                            source_key = f"composition_pct.{element}"
                            if source_key in product["raw_values"]:
                                chemical_detail["raw_value"] = product["raw_values"][source_key]
                    else:
                        source_key = "length_m" if field == "length" else field
                        if source_key in product["raw_values"]:
                            detail["raw_value"] = product["raw_values"][source_key]
                if product["observations"]["length"]["raw_value"] is None:
                    product["coiled"] = None
                for evidence in product["evidence"]:
                    field = evidence.get("field_path")
                    if field and field.startswith("composition_pct."):
                        detail = product["observations"]["composition_pct"].get(field.split(".", 1)[1])
                    else:
                        detail = product["observations"].get("length" if field == "length_m" else field)
                    if detail is not None:
                        detail.update({"raw_value": evidence["source_text"], "page_number": evidence["page"], "bbox": evidence["bbox"], "source_text": evidence["source_text"], "confidence": evidence["confidence"]})
            signals.append(f"products_extracted:{len(product_rows)}")
            return GenericExtractionResult(
                is_valid_certificate=True,
                certificate=normalized,
                unmapped_blocks=unmapped_blocks,
                signals=signals,
                reasons=[],
            )
        except Exception as exc:
            logger.warning("generic_normalization_error", extra={"error": str(exc)})
            return GenericExtractionResult(
                is_valid_certificate=False,
                certificate=None,
                unmapped_blocks=unmapped_blocks,
                signals=signals,
                reasons=[f"Fallo de validación canónica: {exc}"],
            )

    def _extract_metadata(self, document: DocumentLayout) -> dict:
        from backend.app.certificate_parser.metadata import extract_metadata

        return extract_metadata(document)

    def _analyze_table_columns(self, table: TableRegion) -> tuple[int, list[ColumnDefinition]]:
        """Identify header row and column definitions (supports multi-level headers)."""
        if not table.rows:
            return 0, []

        best_header_row = 0
        best_cols: list[ColumnDefinition] = []
        max_identified = 0

        for r_idx in range(min(4, len(table.rows))):
            row = table.rows[r_idx]
            next_row = table.rows[r_idx + 1] if r_idx + 1 < len(table.rows) else None

            # First, check if current row is a group header (e.g. Chemical Composition spanning cols)
            group_context: dict[int, str] = {}
            current_group = ""
            for c_idx, cell in enumerate(row):
                c_text = _clean_cell(cell)
                if c_text:
                    current_group = c_text
                group_context[c_idx] = current_group

            row_text = " ".join(_clean_cell(c) for c in row)
            normalized_row = normalize_term(row_text)
            has_group_keyword = any(
                kw in normalized_row
                for kw in ("quimic", "chem", "dimens", "propied", "mecanic", "identific", "composition", "mechanical", "成分")
            )
            is_group_header = bool(next_row and has_group_keyword and any(not _clean_cell(c) for c in row))

            target_row = next_row if is_group_header else row
            header_offset = 1 if is_group_header else 0

            cols: list[ColumnDefinition] = []
            identified_count = 0

            for c_idx, cell in enumerate(target_row):
                c_text = _clean_cell(cell)
                grp = group_context.get(c_idx, "") if is_group_header else ""
                combined_text = f"{grp} {c_text}".strip()
                cat, key, exp = match_column_semantic(combined_text if grp else c_text)
                if cat == "unknown" and grp and c_text:
                    # Retry matching just c_text
                    cat, key, exp = match_column_semantic(c_text)
                if cat == "chemistry" and exp is None and grp:
                    exp = detect_scale_exponent(grp)
                if cat != "unknown":
                    identified_count += 1
                cols.append(ColumnDefinition(c_idx, cat, key, exp, combined_text))

            if identified_count > max_identified:
                max_identified = identified_count
                best_header_row = r_idx + header_offset
                best_cols = cols

        return best_header_row, best_cols

    def _extract_tables_and_products(self, document: DocumentLayout) -> dict[str, Any]:
        rows: list[dict[str, Any]] = []
        mapped_cell_indices: set[tuple[int, int, int]] = set()  # (page, table_idx, (r, c))
        chemistry_scales: dict[str, int] = {}

        for page in document.pages:
            geometric_rows, geometric_scales = recover_rows(page)
            if geometric_rows:
                for raw_row in geometric_rows:
                    row = {"table_scope": (page.page_number, "geometry"), "product_id": raw_row["product_id"], "chemistry": {}, "evidence": raw_row["evidence"], "chemistry_scales": geometric_scales}
                    for key, value in raw_row.items():
                        if key in {"product_id", "evidence", "chemistry", "dimension_headers"}:
                            continue
                        if key == "label_no":
                            row[key] = value
                            continue
                        category = "heat_no" if key == "heat_no" else "mechanical" if key.endswith(("_mpa", "_pct", "_hrb")) else "dimension"
                        self._apply_value(row, ColumnDefinition(0, category, key, header=raw_row.get("dimension_headers", {}).get(key, "")), value)
                    for key, value in raw_row["chemistry"].items():
                        if _is_ditto(value) or _parse_numeric(value) is not None:
                            self._apply_value(row, ColumnDefinition(0, "chemistry", key), value)
                    rows.append(row)
                chemistry_scales.update(geometric_scales)
                continue
            for t_idx, table in enumerate(page.tables):
                header_idx, cols = self._analyze_table_columns(table)
                if not any(c.category in {"product_id", "heat_no"} for c in cols):
                    continue

                for col in cols:
                    if col.category == "chemistry" and col.canonical_key:
                        if col.exponent is not None:
                            chemistry_scales[col.canonical_key] = col.exponent

                for r_idx in range(header_idx + 1, len(table.rows)):
                    raw_row = table.rows[r_idx]
                    first_non_empty = next((_clean_cell(c) for c in raw_row if _clean_cell(c)), "")
                    if not first_non_empty or "total" in normalize_term(first_non_empty):
                        continue

                    product_dict: dict[str, Any] = {
                        "table_scope": (page.page_number, t_idx),
                        "product_id": None,
                        "heat_no": None,
                        "thickness_mm": None,
                        "width_mm": None,
                        "length_raw": None,
                        "weight_kg": None,
                        "chemistry": {},
                        "evidence": [{"page": page.page_number, "table_row": r_idx}],
                        "chemistry_scales": dict(chemistry_scales),
                    }
                    row_mapped_cells: set[tuple[int, int, int]] = set()

                    for col in cols:
                        if col.index >= len(raw_row):
                            continue
                        cell_val = _clean_cell(raw_row[col.index])
                        if not cell_val:
                            continue

                        if col.category != "unknown":
                            if col.category == "chemistry" and col.exponent is None:
                                continue
                            self._apply_value(product_dict, col, cell_val)
                            key = "length_raw" if col.canonical_key == "length_m" else col.canonical_key
                            mapped = product_dict["chemistry"].get(key) if col.category == "chemistry" else product_dict.get(key)
                            if mapped is not None:
                                row_mapped_cells.add((page.page_number, t_idx, r_idx * 1000 + col.index))

                    if product_dict.get("product_id"):
                        rows.append(product_dict)
                        mapped_cell_indices.update(row_mapped_cells)

        return {
            "rows": rows,
            "chemistry_scales": chemistry_scales,
            "mapped_cell_indices": mapped_cell_indices,
        }

    def _apply_value(
        self,
        product: dict[str, Any],
        col: ColumnDefinition,
        value: Any,
    ) -> None:
        str_val = str(value).strip()
        if not str_val:
            return
        source_key = f"composition_pct.{col.canonical_key}" if col.category == "chemistry" else col.canonical_key
        product.setdefault("raw_values", {})[source_key] = str_val

        if col.category == "product_id":
            product["product_id"] = str_val

        elif col.category == "heat_no":
            product["heat_no"] = str_val

        elif col.category == "dimension" and col.canonical_key:
            if _is_ditto(str_val):
                product["length_raw" if col.canonical_key == "length_m" else col.canonical_key] = str_val
                return

            if re.search(r"[xX×*]", str_val) and col.canonical_key == "thickness_mm":
                parts = re.split(r"[xX×*]", str_val)
                if len(parts) >= 2:
                    # shortcut: unordered imperial size tuples stay evidence; resolve with explicit dimension labels.
                    if dimension_unit(str_val + ' ' + col.header) in {'in', 'ft'} and not re.search(r'thickness|espesor', col.header, re.I):
                        return
                    th = dimension_value(parts[0], col.header)
                    wi = dimension_value(parts[1], col.header)
                    if th is not None:
                        product["thickness_mm"] = th
                    if wi is not None:
                        product["width_mm"] = wi
                    if len(parts) >= 3 and parts[2].upper().startswith("C"):
                        product["coiled"] = True
                        product["length_raw"] = "C"
                    elif len(parts) >= 3:
                        product["length_raw"] = dimension_value(parts[2], col.header or "mm", length=True)
                    return

            if col.canonical_key == "length_m":
                if str_val.upper() in {"C", "COIL", "ROLLO"}:
                    product["length_raw"] = "COIL"
                    product["coiled"] = True
                else:
                    num = dimension_value(str_val, col.header, length=True)
                    if num is not None:
                        product["length_raw"] = num
            else:
                numeric_text = str_val
                if col.canonical_key == "thickness_mm" and re.fullmatch(r"\d+,\d+", str_val):
                    numeric_text = str_val.replace(",", ".")
                elif col.canonical_key in {"weight_kg", "net_weight_kg", "gross_weight_kg"} and re.fullmatch(r"\d{1,3}\.\d{3}", str_val):
                    numeric_text = str_val.replace(".", "")
                if col.canonical_key == 'width_mm' and dimension_unit(str_val) is None:
                    numeric = _parse_numeric(str_val)
                    if numeric is not None:
                        numeric_text = str(numeric)
                num = dimension_value(numeric_text, col.header) if col.canonical_key in {"thickness_mm", "width_mm"} else _parse_numeric(numeric_text)
                if num is not None:
                    product[col.canonical_key] = num

        elif col.category == "chemistry" and col.canonical_key:
            if _is_ditto(str_val):
                product["chemistry"][col.canonical_key] = str_val
            else:
                num = _parse_numeric(str_val)
                if num is not None:
                    product["chemistry"][col.canonical_key] = num

        elif col.category == "mechanical" and col.canonical_key:
            num = None if _is_ditto(str_val) else _parse_numeric(str_val)
            if num is not None:
                if col.canonical_key == "elongation_pct" and not 0 <= num <= 100:
                    return
                if col.canonical_key == "hardness_hrb" and not 0 <= num <= 150:
                    return
                product[col.canonical_key] = num

    def _collect_unmapped(
        self,
        document: DocumentLayout,
        mapped_cells: set[tuple[int, int, int]],
    ) -> list[dict[str, Any]]:
        unmapped: list[dict[str, Any]] = []
        for page in document.pages:
            for block in page.blocks:
                label = normalize_term(re.split(r"[:：\-]", block.text, maxsplit=1)[0])
                is_metadata = block.bbox.top <= page.height * 0.45 and any(
                    label == alias
                    for aliases in METADATA_LABELS.values()
                    for alias in aliases
                )
                if block.text.strip() and not is_metadata:
                    unmapped.append({
                        "kind": "text_block",
                        "page_number": page.page_number,
                        "text": block.text,
                        "bbox": block.bbox.as_dict(),
                        "confidence": block.confidence,
                    })
            for table_idx, table in enumerate(page.tables):
                for row_idx, row in enumerate(table.rows):
                    for column_idx, cell in enumerate(row):
                        text = _clean_cell(cell)
                        cell_key = (page.page_number, table_idx, row_idx * 1000 + column_idx)
                        if text and cell_key not in mapped_cells:
                            unmapped.append({
                                "kind": "table_cell",
                                "page_number": page.page_number,
                                "table_index": table_idx,
                                "row_index": row_idx,
                                "column_index": column_idx,
                                "text": text,
                                "bbox": table.bbox.as_dict(),
                                "confidence": None,
                            })
        return unmapped
