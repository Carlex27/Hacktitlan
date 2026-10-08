"""Application service for known and previously unseen certificate layouts."""

from __future__ import annotations

from dataclasses import asdict
from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol

from backend.app.certificate_parser.adapters import AdapterRegistry
from backend.app.certificate_parser.detection import DocumentKind, detect_document_kind
from backend.app.certificate_parser.mill_certificate import normalize_certificate
from backend.app.certificate_parser.semantics import (
    discover_field_candidates,
    discover_table_candidates,
)
from backend.app.domain.document import DocumentLayout


class DocumentReader(Protocol):
    def read(self, path: str | Path) -> DocumentLayout: ...


class ExtractionStatus(StrEnum):
    EXTRACTED = "extracted"
    NEEDS_REVIEW = "needs_review"
    NEEDS_OCR = "needs_ocr"
    UNSUPPORTED = "unsupported"


class CertificateExtractionService:
    """Coordinate deterministic ingestion, detection and known adapters.

    No AI implementation is used. An unknown but plausible certificate returns
    semantic evidence for review instead of fabricated product values.
    """

    def __init__(self, reader: DocumentReader, adapters: AdapterRegistry | None = None) -> None:
        self.reader = reader
        self.adapters = adapters or AdapterRegistry()

    def analyze_pdf(self, path: str | Path) -> dict[str, Any]:
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

        adapter = self.adapters.best_match(document)
        if adapter is not None:
            raw_payload = adapter.extract(document)
            return {
                **base,
                "status": ExtractionStatus.EXTRACTED.value,
                "adapter": adapter.name,
                "certificate": normalize_certificate(raw_payload),
            }

        status = (
            ExtractionStatus.NEEDS_REVIEW
            if detection.kind is not DocumentKind.UNKNOWN
            else ExtractionStatus.UNSUPPORTED
        )
        return {**base, "status": status.value}

    def release(self) -> None:
        release = getattr(self.reader, "release", None)
        if callable(release):
            release()

    @staticmethod
    def normalize_known_payload(raw_payload: dict[str, Any]) -> dict[str, Any]:
        """Keep the existing four-format normalization path available."""

        return normalize_certificate(raw_payload)

