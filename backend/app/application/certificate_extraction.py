"""Application service for known and previously unseen certificate layouts."""

from __future__ import annotations

from dataclasses import asdict
from enum import StrEnum
from pathlib import Path
from typing import Any, Callable, Protocol

from backend.app.certificate_parser.adapters import AdapterRegistry
from backend.app.certificate_parser.detection import DocumentKind, detect_document_kind
from backend.app.certificate_parser.format_profiles import evaluate_format_profiles
from backend.app.certificate_parser.generic_extractor import GenericCertificateExtractor
from backend.app.certificate_parser.mill_certificate import normalize_certificate
from backend.app.certificate_parser.semantics import (
    discover_field_candidates,
    discover_table_candidates,
)
from backend.app.domain.document import DocumentLayout


class DocumentReader(Protocol):
    def read(self, path: str | Path, **kwargs: Any) -> DocumentLayout: ...


class ExtractionStatus(StrEnum):
    EXTRACTED = "extracted"
    NEEDS_REVIEW = "needs_review"
    NEEDS_OCR = "needs_ocr"
    UNSUPPORTED = "unsupported"


class CertificateExtractionService:
    """Coordinate deterministic ingestion, detection, known adapters, and generic extraction.

    No ML hallucinations are used. Unknown layouts produce canonical structures with
    evidence and status needs_review, preserving unmapped blocks for human audit.
    """

    def __init__(
        self,
        reader: DocumentReader,
        adapters: AdapterRegistry | None = None,
        generic_extractor: GenericCertificateExtractor | None = None,
    ) -> None:
        self.reader = reader
        self.adapters = adapters or AdapterRegistry()
        self.generic_extractor = generic_extractor or GenericCertificateExtractor()

    def analyze_pdf(
        self,
        path: str | Path,
        *,
        page_callback: Callable[[int, int], None] | None = None,
        cancel_check: Callable[[], bool] | None = None,
    ) -> dict[str, Any]:
        try:
            document = self.reader.read(path, page_callback=page_callback, cancel_check=cancel_check)
        except TypeError:
            document = self.reader.read(path)
        detection = detect_document_kind(document)
        fields = discover_field_candidates(document)
        tables = discover_table_candidates(document)

        base: dict[str, Any] = {
            "document": {
                "file_name": document.file_name,
                "sha256": document.sha256,
                "page_count": len(document.pages),
                "ingestion": document.metadata,
            },
            "detection": {
                "kind": detection.kind.value,
                "confidence": detection.confidence,
                "signals": list(detection.signals),
            },
            "field_candidates": [asdict(candidate) for candidate in fields],
            "table_candidates": [asdict(candidate) for candidate in tables],
        }
        if document.requires_ocr:
            return {**base, "status": ExtractionStatus.NEEDS_OCR.value}

        # Step 1: Strict evaluation of known format profiles (threshold >= 0.85)
        profile_name, profile_score, profile_signals = evaluate_format_profiles(
            document, min_confidence=0.85
        )
        if profile_name is not None:
            adapter = self.adapters.match_profile(
                profile_name, document, minimum_confidence=0.85
            )
            if adapter is not None:
                raw_payload = adapter.extract(document)
                return {
                    **base,
                    "status": ExtractionStatus.EXTRACTED.value,
                    "adapter": adapter.name,
                    "certificate": normalize_certificate(raw_payload),
                }
            return {
                **base,
                "status": ExtractionStatus.NEEDS_REVIEW.value,
                "profile": {
                    "name": profile_name,
                    "confidence": profile_score,
                    "signals": list(profile_signals),
                },
                "reasons": [
                    f"El formato conocido {profile_name} no tiene un adaptador registrado"
                ],
            }

        # Step 2: Generic deterministic extraction for unknown formats
        generic_result = self.generic_extractor.extract(document)
        if generic_result.is_valid_certificate and generic_result.certificate is not None:
            return {
                **base,
                "status": ExtractionStatus.NEEDS_REVIEW.value,
                "adapter": "generic_layout_extractor",
                "certificate": generic_result.certificate,
                "unmapped_blocks": generic_result.unmapped_blocks,
                "signals": list(detection.signals) + generic_result.signals,
            }

        status = (
            ExtractionStatus.NEEDS_REVIEW
            if detection.kind is not DocumentKind.UNKNOWN
            else ExtractionStatus.UNSUPPORTED
        )
        return {
            **base,
            "status": status.value,
            "unmapped_blocks": generic_result.unmapped_blocks,
            "reasons": generic_result.reasons,
        }

    def release(self) -> None:
        release = getattr(self.reader, "release", None)
        if callable(release):
            release()

    @staticmethod
    def normalize_known_payload(raw_payload: dict[str, Any]) -> dict[str, Any]:
        """Keep the existing four-format normalization path available."""

        return normalize_certificate(raw_payload)
