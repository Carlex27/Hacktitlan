"""Deterministic vocabulary and semantic discovery for unseen layouts."""

from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata

from backend.app.domain.document import BoundingBox, DocumentLayout


FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "product_id": ("coil no", "coil number", "coil id", "pack no", "roll no", "bundle no"),
    "heat_no": ("heat no", "heat number", "cast no", "melt no", "charge no", "colada", "炉号"),
    "thickness_mm": ("thick", "thickness", "gauge", "espesor"),
    "width_mm": ("width", "ancho"),
    "length_raw": ("length", "largo", "longitud"),
    "weight_kg": ("weight", "mass", "net weight", "gross weight", "peso", "重量"),
    "chemistry": ("chemical composition", "chemical analysis", "ladle analysis", "composicion quimica", "化学成分"),
    "standard": ("standard", "specification", "spec", "grade", "norma"),
    "yield_strength_mpa": ("yield point", "yield strength", "proof stress", "limite elastico"),
    "tensile_strength_mpa": ("tensile strength", "resistencia a la traccion"),
}

TITLE_ALIASES = (
    "mill test certificate",
    "mill certificate",
    "inspection certificate",
    "certificate of quality",
    "material test certificate",
    "test certificate",
    "certificado de molino",
    "质量证明书",
)


def normalize_label(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    without_marks = "".join(char for char in normalized if not unicodedata.combining(char))
    return re.sub(r"[^\w]+", " ", without_marks, flags=re.UNICODE).strip()


NORMALIZED_FIELD_ALIASES = {
    field: tuple(normalize_label(alias) for alias in aliases)
    for field, aliases in FIELD_ALIASES.items()
}


@dataclass(frozen=True)
class FieldCandidate:
    field: str
    source_text: str
    page_number: int
    bbox: BoundingBox | None
    confidence: float


@dataclass(frozen=True)
class TableCandidate:
    page_number: int
    bbox: BoundingBox
    header_row_index: int
    columns: dict[int, str]
    row_count: int
    confidence: float


def identify_field(value: str) -> tuple[str, float] | None:
    candidate = normalize_label(value)
    if not candidate:
        return None
    best: tuple[str, float] | None = None
    for field, aliases in NORMALIZED_FIELD_ALIASES.items():
        for alias in aliases:
            if candidate == alias:
                score = 0.99
            elif candidate.startswith(alias) or candidate.endswith(alias):
                score = 0.92
            elif len(alias) >= 4 and alias in candidate:
                score = 0.84
            else:
                continue
            if best is None or score > best[1]:
                best = (field, score)
    return best


def discover_field_candidates(document: DocumentLayout) -> tuple[FieldCandidate, ...]:
    candidates: list[FieldCandidate] = []
    seen: set[tuple[str, int]] = set()
    for page in document.pages:
        for block in page.blocks:
            identified = identify_field(block.text)
            if identified:
                field, confidence = identified
                candidates.append(
                    FieldCandidate(field, block.text, page.page_number, block.bbox, confidence)
                )
                seen.add((field, page.page_number))
        # Native PDF extraction commonly returns one block per word. Search the
        # full page as a fallback so multi-word labels such as "HEAT NO" remain
        # discoverable without assuming fixed coordinates.
        normalized_page = normalize_label(page.text)
        for field, aliases in NORMALIZED_FIELD_ALIASES.items():
            if (field, page.page_number) in seen:
                continue
            matched_alias = next((alias for alias in aliases if alias in normalized_page), None)
            if matched_alias:
                candidates.append(
                    FieldCandidate(field, matched_alias, page.page_number, None, 0.80)
                )
                seen.add((field, page.page_number))
        for table in page.tables:
            for row in table.rows[:6]:
                for cell in row:
                    if not cell:
                        continue
                    identified = identify_field(cell)
                    if not identified:
                        continue
                    field, confidence = identified
                    if (field, page.page_number) not in seen:
                        candidates.append(
                            FieldCandidate(field, cell, page.page_number, table.bbox, confidence)
                        )
                        seen.add((field, page.page_number))
    return tuple(candidates)


def discover_table_candidates(document: DocumentLayout) -> tuple[TableCandidate, ...]:
    candidates: list[TableCandidate] = []
    for page in document.pages:
        for table in page.tables:
            best_row: tuple[int, dict[int, str], float] | None = None
            for row_index, row in enumerate(table.rows[:6]):
                columns: dict[int, str] = {}
                scores: list[float] = []
                for column_index, cell in enumerate(row):
                    if not cell:
                        continue
                    identified = identify_field(cell)
                    if identified:
                        columns[column_index], confidence = identified
                        scores.append(confidence)
                unique_fields = len(set(columns.values()))
                if unique_fields < 2:
                    continue
                score = min(0.99, (sum(scores) / len(scores)) * min(1.0, unique_fields / 4))
                if best_row is None or score > best_row[2]:
                    best_row = (row_index, columns, score)
            if best_row:
                row_index, columns, confidence = best_row
                candidates.append(
                    TableCandidate(
                        page_number=page.page_number,
                        bbox=table.bbox,
                        header_row_index=row_index,
                        columns=columns,
                        row_count=max(0, len(table.rows) - row_index - 1),
                        confidence=confidence,
                    )
                )
    return tuple(candidates)

