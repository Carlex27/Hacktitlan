"""Deterministic generic certificate extractor for previously unseen mill certificate layouts."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal
import logging
import re
from typing import Any

from backend.app.certificate_parser.mill_certificate import normalize_certificate
from backend.app.certificate_parser.vocabulary import (
    DITTO_TOKENS,
    METADATA_LABELS,
    match_column_semantic,
    normalize_term,
)
from backend.app.domain.document import DocumentLayout, PageLayout, TableRegion, TextBlock
from backend.app.normalization.chemistry import normalize_scaled_percentage

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ColumnDefinition:
    index: int
    category: str  # "product_id", "heat_no", "dimension", "chemistry", "mechanical", "unknown"
    canonical_key: str | None
    exponent: int | None = None


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
            },
            "standard": metadata.get("standard"),
            "chemistry_scales": tables_data.get("chemistry_scales", {}),
            "rows": product_rows,
            "unmapped_blocks": unmapped_blocks,
        }

        try:
            normalized = normalize_certificate(raw_payload)
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

    def _extract_metadata(self, document: DocumentLayout) -> dict[str, str | None]:
        metadata: dict[str, str | None] = {
            "certificate_no": None,
            "supplier": None,
            "standard": None,
            "issue_date": None,
            "customer": None,
        }
        if not document.pages:
            return metadata

        page1 = document.pages[0]
        # Look through blocks on top half of page 1
        blocks = [b for b in page1.blocks if b.bbox.top <= page1.height * 0.45]
        text_lines = [b.text.strip() for b in blocks if b.text.strip()]

        for i, line in enumerate(text_lines):
            clean_line = normalize_term(line)
            for meta_key, aliases in METADATA_LABELS.items():
                if metadata[meta_key] is not None:
                    continue
                for alias in aliases:
                    if alias in clean_line:
                        # Extract value after colon or following word
                        parts = re.split(r"[:：\-]", line, maxsplit=1)
                        if len(parts) > 1 and parts[1].strip():
                            metadata[meta_key] = parts[1].strip()
                        elif i + 1 < len(text_lines) and not any(
                            a in normalize_term(text_lines[i + 1])
                            for sublist in METADATA_LABELS.values()
                            for a in sublist
                        ):
                            metadata[meta_key] = text_lines[i + 1].strip()
                        break

        # Also search tables header cells for metadata if not found
        for table in page1.tables:
            for row in table.rows[:3]:
                for cell_idx, cell in enumerate(row):
                    if not cell:
                        continue
                    clean_cell = normalize_term(cell)
                    for meta_key, aliases in METADATA_LABELS.items():
                        if metadata[meta_key] is not None:
                            continue
                        for alias in aliases:
                            if alias in clean_cell:
                                # Check neighboring cell in table
                                if cell_idx + 1 < len(row) and row[cell_idx + 1]:
                                    metadata[meta_key] = str(row[cell_idx + 1]).strip()
                                break

        return metadata

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
                cols.append(ColumnDefinition(c_idx, cat, key, exp))

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
            for t_idx, table in enumerate(page.tables):
                header_idx, cols = self._analyze_table_columns(table)
                if not any(c.category in {"product_id", "heat_no"} for c in cols):
                    continue

                for col in cols:
                    if col.category == "chemistry" and col.canonical_key:
                        scale = col.exponent if col.exponent is not None else 0
                        chemistry_scales[col.canonical_key] = scale

                for r_idx in range(header_idx + 1, len(table.rows)):
                    raw_row = table.rows[r_idx]
                    first_non_empty = next((_clean_cell(c) for c in raw_row if _clean_cell(c)), "")
                    if not first_non_empty or "total" in normalize_term(first_non_empty):
                        continue

                    product_dict: dict[str, Any] = {
                        "product_id": None,
                        "heat_no": None,
                        "thickness_mm": None,
                        "width_mm": None,
                        "length_raw": None,
                        "weight_kg": None,
                        "chemistry": {},
                        "evidence": [{"page": page.page_number, "table_row": r_idx}],
                    }
                    row_mapped_cells: set[tuple[int, int, int]] = set()

                    for col in cols:
                        if col.index >= len(raw_row):
                            continue
                        cell_val = _clean_cell(raw_row[col.index])
                        if not cell_val:
                            continue

                        if col.category != "unknown":
                            row_mapped_cells.add(
                                (page.page_number, t_idx, r_idx * 1000 + col.index)
                            )
                            self._apply_value(product_dict, col, cell_val)

                    has_material_data = any(
                        product_dict.get(key) not in (None, "", {})
                        for key in (
                            "thickness_mm",
                            "width_mm",
                            "length_raw",
                            "weight_kg",
                            "chemistry",
                            "yield_strength_mpa",
                            "tensile_strength_mpa",
                            "elongation_pct",
                            "hardness_hrb",
                        )
                    )
                    if product_dict.get("product_id") and has_material_data:
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

        if col.category == "product_id":
            product["product_id"] = str_val

        elif col.category == "heat_no":
            product["heat_no"] = str_val

        elif col.category == "dimension" and col.canonical_key:
            if _is_ditto(str_val):
                product[col.canonical_key] = str_val
                return

            if "x" in str_val.lower() and col.canonical_key == "thickness_mm":
                parts = re.split(r"[xX*]", str_val)
                if len(parts) >= 2:
                    th = _parse_numeric(parts[0])
                    wi = _parse_numeric(parts[1])
                    if th is not None:
                        product["thickness_mm"] = th
                    if wi is not None:
                        product["width_mm"] = wi
                    if len(parts) >= 3 and parts[2].upper().startswith("C"):
                        product["coiled"] = True
                        product["length_raw"] = "C"
                    return

            if col.canonical_key == "length_m":
                if str_val.upper() in {"C", "COIL", "ROLLO"}:
                    product["length_raw"] = "COIL"
                    product["coiled"] = True
                else:
                    num = _parse_numeric(str_val)
                    product["length_raw"] = num if num is not None else str_val
            else:
                num = _parse_numeric(str_val)
                product[col.canonical_key] = num if num is not None else str_val

        elif col.category == "chemistry" and col.canonical_key:
            if _is_ditto(str_val):
                product["chemistry"][col.canonical_key] = str_val
            else:
                num = _parse_numeric(str_val)
                product["chemistry"][col.canonical_key] = num if num is not None else str_val

        elif col.category == "mechanical" and col.canonical_key:
            num = None if _is_ditto(str_val) else _parse_numeric(str_val)
            product[col.canonical_key] = str_val if num is None else num

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
