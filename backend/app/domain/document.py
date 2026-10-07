"""Layout-aware document primitives shared by ingestion and parsing."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class PageSource(StrEnum):
    DIGITAL = "digital"
    OCR = "ocr"
    UNREADABLE = "unreadable"


@dataclass(frozen=True)
class BoundingBox:
    x0: float
    top: float
    x1: float
    bottom: float

    def __post_init__(self) -> None:
        if self.x1 < self.x0 or self.bottom < self.top:
            raise ValueError("Invalid bounding box coordinates")

    def as_dict(self) -> dict[str, float]:
        return {"x0": self.x0, "top": self.top, "x1": self.x1, "bottom": self.bottom}


@dataclass(frozen=True)
class TextBlock:
    page_number: int
    text: str
    bbox: BoundingBox
    confidence: float = 1.0
    source: PageSource = PageSource.DIGITAL


@dataclass(frozen=True)
class TableRegion:
    page_number: int
    bbox: BoundingBox
    rows: tuple[tuple[str | None, ...], ...]


@dataclass(frozen=True)
class PageLayout:
    page_number: int
    width: float
    height: float
    rotation: int
    source: PageSource
    blocks: tuple[TextBlock, ...] = ()
    tables: tuple[TableRegion, ...] = ()

    @property
    def text(self) -> str:
        return " ".join(block.text for block in self.blocks if block.text.strip())


@dataclass(frozen=True)
class DocumentLayout:
    file_name: str
    sha256: str
    pages: tuple[PageLayout, ...]
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def text(self) -> str:
        return "\n".join(page.text for page in self.pages)

    @property
    def requires_ocr(self) -> bool:
        return any(page.source is PageSource.UNREADABLE for page in self.pages)

