"""Select evidence from page-relative regions without interpreting its values."""

from dataclasses import dataclass
from math import isfinite
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.app.domain.document import BoundingBox, PageLayout, PageSource, TextBlock


class PageRegion(BaseModel):
    """Coordinates on the already oriented layout, independent of display zoom."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    x0: float = Field(ge=0, le=1)
    top: float = Field(ge=0, le=1)
    x1: float = Field(ge=0, le=1)
    bottom: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def positive_area(self) -> "PageRegion":
        if self.x0 >= self.x1 or self.top >= self.bottom:
            raise ValueError("La región debe tener ancho y alto positivos")
        return self

    def to_bbox(self, page: PageLayout) -> BoundingBox:
        _validate_page_size(page)
        return BoundingBox(self.x0 * page.width, self.top * page.height,
                           self.x1 * page.width, self.bottom * page.height)

    @classmethod
    def from_bbox(cls, bbox: BoundingBox, page: PageLayout) -> "PageRegion":
        _validate_page_size(page)
        return cls(x0=bbox.x0 / page.width, top=bbox.top / page.height,
                   x1=bbox.x1 / page.width, bottom=bbox.bottom / page.height)


def _validate_page_size(page: PageLayout) -> None:
    if not all(isfinite(value) and value > 0 for value in (page.width, page.height)):
        raise ValueError("Dimensiones de página inválidas")


@dataclass(frozen=True)
class RegionEvidence:
    page_number: int
    bbox: BoundingBox
    status: Literal["success", "empty", "needs_review", "needs_ocr"]
    blocks: tuple[TextBlock, ...]
    partial_blocks: tuple[TextBlock, ...]

    @property
    def text(self) -> str:
        return " ".join(block.text for block in self.blocks)


def select_region(page: PageLayout, region: PageRegion) -> RegionEvidence:
    """Retain complete blocks and report clipped words instead of guessing values."""
    bbox = region.to_bbox(page)
    if page.source is PageSource.UNREADABLE:
        return RegionEvidence(page.page_number, bbox, "needs_ocr", (), ())
    complete: list[TextBlock] = []
    partial: list[TextBlock] = []
    # Relative-coordinate round trips can move an edge by floating-point noise.
    epsilon = 1e-7
    # Preserve ingestion order; reconstructing tables is a separate extraction step.
    for block in page.blocks:
        box = block.bbox
        if not all(isfinite(value) for value in (box.x0, box.top, box.x1, box.bottom)):
            raise ValueError("Geometría de texto inválida")
        if box.x0 >= box.x1 or box.top >= box.bottom:
            raise ValueError("El bloque de texto debe tener área positiva")
        if (bbox.x0 - epsilon <= box.x0 and bbox.top - epsilon <= box.top
                and box.x1 <= bbox.x1 + epsilon and box.bottom <= bbox.bottom + epsilon):
            complete.append(block)
        elif max(bbox.x0, box.x0) < min(bbox.x1, box.x1) and max(bbox.top, box.top) < min(bbox.bottom, box.bottom):
            partial.append(block)
    status: Literal["success", "empty", "needs_review", "needs_ocr"] = (
        "needs_review" if partial else "success" if complete else "empty"
    )
    return RegionEvidence(page.page_number, bbox, status, tuple(complete), tuple(partial))
