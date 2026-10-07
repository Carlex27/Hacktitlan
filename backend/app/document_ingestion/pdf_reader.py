"""Extract digital PDF text, geometry and tables without applying business rules."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Any

from backend.app.domain.document import (
    BoundingBox,
    DocumentLayout,
    PageLayout,
    PageSource,
    TableRegion,
    TextBlock,
)


class DocumentIngestionError(ValueError):
    """Raised when an input cannot be safely opened as a PDF."""


class PdfPlumberReader:
    """Read a PDF's native text layer.

    Image-only pages are explicitly marked as unreadable so an OCR provider can
    be added later. They are never treated as empty certificates.
    """

    def __init__(self, minimum_digital_characters: int = 20) -> None:
        self.minimum_digital_characters = minimum_digital_characters

    def read(self, path: str | Path) -> DocumentLayout:
        input_path = Path(path)
        if input_path.suffix.lower() != ".pdf":
            raise DocumentIngestionError("Only PDF documents are accepted")
        if not input_path.is_file():
            raise DocumentIngestionError(f"PDF does not exist: {input_path}")

        try:
            import pdfplumber
        except ImportError as exc:  # pragma: no cover - deployment guard
            raise DocumentIngestionError("pdfplumber is required for digital PDF ingestion") from exc

        try:
            with pdfplumber.open(input_path) as pdf:
                pages = tuple(self._read_page(page, index) for index, page in enumerate(pdf.pages, 1))
                metadata = dict(pdf.metadata or {})
        except Exception as exc:
            raise DocumentIngestionError(f"Could not read PDF {input_path.name}: {exc}") from exc

        if not pages:
            raise DocumentIngestionError("The PDF contains no pages")
        return DocumentLayout(
            file_name=input_path.name,
            sha256=sha256(input_path.read_bytes()).hexdigest(),
            pages=pages,
            metadata=metadata,
        )

    def _read_page(self, page: Any, page_number: int) -> PageLayout:
        words = page.extract_words(
            use_text_flow=True,
            keep_blank_chars=False,
            extra_attrs=[],
        ) or []
        digital_characters = sum(len(str(word.get("text", "")).strip()) for word in words)
        fragmented_ascii_tokens = sum(
            1
            for word in words
            if len(str(word.get("text", "")).strip()) == 1
            and str(word.get("text", "")).isascii()
            and str(word.get("text", "")).isalnum()
        )
        fragmented_text_layer = bool(words) and fragmented_ascii_tokens / len(words) >= 0.70
        source = (
            PageSource.DIGITAL
            if digital_characters >= self.minimum_digital_characters and not fragmented_text_layer
            else PageSource.UNREADABLE
        )
        blocks = tuple(
            TextBlock(
                page_number=page_number,
                text=str(word["text"]),
                bbox=BoundingBox(
                    float(word["x0"]),
                    float(word["top"]),
                    float(word["x1"]),
                    float(word["bottom"]),
                ),
                source=source,
            )
            for word in words
            if str(word.get("text", "")).strip()
        )
        tables: list[TableRegion] = []
        if source is PageSource.DIGITAL:
            for table in page.find_tables() or []:
                extracted = table.extract() or []
                rows = tuple(
                    tuple(None if cell is None else str(cell).strip() for cell in row)
                    for row in extracted
                )
                if not rows:
                    continue
                x0, top, x1, bottom = table.bbox
                tables.append(
                    TableRegion(
                        page_number=page_number,
                        bbox=BoundingBox(float(x0), float(top), float(x1), float(bottom)),
                        rows=rows,
                    )
                )
        return PageLayout(
            page_number=page_number,
            width=float(page.width),
            height=float(page.height),
            rotation=int(getattr(page, "rotation", 0) or 0),
            source=source,
            blocks=blocks,
            tables=tuple(tables),
        )

