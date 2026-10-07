"""Conservative, format-independent mill-certificate detection."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from backend.app.certificate_parser.semantics import (
    NORMALIZED_FIELD_ALIASES,
    TITLE_ALIASES,
    discover_field_candidates,
    normalize_label,
)
from backend.app.domain.document import DocumentLayout


class DocumentKind(StrEnum):
    MILL_CERTIFICATE = "mill_certificate"
    POSSIBLE_MILL_CERTIFICATE = "possible_mill_certificate"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class DetectionResult:
    kind: DocumentKind
    confidence: float
    signals: tuple[str, ...]


def detect_document_kind(document: DocumentLayout) -> DetectionResult:
    normalized_text = normalize_label(document.text)
    title_match = next(
        (alias for alias in TITLE_ALIASES if normalize_label(alias) in normalized_text),
        None,
    )
    fields = {candidate.field for candidate in discover_field_candidates(document)}
    signals: list[str] = []
    score = 0.0

    if title_match:
        score += 0.45
        signals.append(f"title:{title_match}")
    if fields & {"product_id", "heat_no"}:
        score += 0.25
        signals.append("product-identifiers")
    if "chemistry" in fields:
        score += 0.20
        signals.append("chemical-analysis")
    if fields & {"thickness_mm", "width_mm", "weight_kg"}:
        score += 0.10
        signals.append("product-properties")

    # A title by itself is not enough, and a generic table without material
    # evidence must not be silently accepted as a certificate.
    has_identity = bool(fields & {"product_id", "heat_no"})
    has_material_data = "chemistry" in fields or bool(
        fields & {"thickness_mm", "width_mm", "yield_strength_mpa"}
    )
    if score >= 0.65 and has_identity and has_material_data:
        kind = DocumentKind.MILL_CERTIFICATE
    elif score >= 0.35 and (has_identity or has_material_data):
        kind = DocumentKind.POSSIBLE_MILL_CERTIFICATE
    else:
        kind = DocumentKind.UNKNOWN
    return DetectionResult(kind=kind, confidence=round(score, 2), signals=tuple(signals))

