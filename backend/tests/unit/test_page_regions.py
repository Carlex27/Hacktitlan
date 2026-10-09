from dataclasses import replace

import pytest
from pydantic import ValidationError

from backend.app.certificate_parser import PageRegion, select_region
from backend.app.domain.document import BoundingBox, PageLayout, PageSource, TextBlock


def page() -> PageLayout:
    return PageLayout(3, 600, 800, 0, PageSource.DIGITAL, blocks=(
        TextBlock(3, "COIL-123", BoundingBox(60, 80, 120, 100)),
        TextBlock(3, "HEAT-456", BoundingBox(150, 80, 230, 100)),
    ))


@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
def test_region_round_trip_uses_oriented_page_size_without_rotating_twice(rotation):
    layout = replace(page(), rotation=rotation, width=800 if rotation in (90, 270) else 600,
                     height=600 if rotation in (90, 270) else 800)
    box = layout.blocks[0].bbox
    region = PageRegion.from_bbox(box, layout)
    assert region.to_bbox(layout) == box
    result = select_region(layout, region)
    assert result.status == "success"
    assert result.page_number == 3
    assert result.text == "COIL-123"
    assert result.blocks == (layout.blocks[0],)


@pytest.mark.parametrize("updates", [
    {"x0": -0.1}, {"x1": 1.1}, {"top": float("nan")}, {"bottom": float("inf")},
    {"x0": 0.5, "x1": 0.4}, {"bottom": 0}, {"script": "ignored?"},
])
def test_invalid_regions_are_rejected(updates):
    with pytest.raises(ValidationError):
        PageRegion.model_validate({"x0": 0, "top": 0, "x1": 1, "bottom": 1, **updates})


def test_cut_word_is_reported_without_silent_partial_value():
    result = select_region(page(), PageRegion(x0=0, top=0, x1=0.3, bottom=1))
    assert result.status == "needs_review"
    assert result.text == "COIL-123"
    assert result.partial_blocks == (page().blocks[1],)


def test_unreadable_page_is_not_an_empty_selection():
    result = select_region(replace(page(), source=PageSource.UNREADABLE),
                           PageRegion(x0=0, top=0, x1=1, bottom=1))
    assert result.status == "needs_ocr"
    assert result.text == ""


def test_readable_empty_region_is_explicit():
    result = select_region(page(), PageRegion(x0=0, top=0.5, x1=1, bottom=1))
    assert result.status == "empty"


def test_ocr_evidence_preserves_confidence_and_source():
    block = replace(page().blocks[0], source=PageSource.OCR, confidence=0.62)
    layout = replace(page(), source=PageSource.OCR, blocks=(block,))
    result = select_region(layout, PageRegion(x0=0, top=0, x1=1, bottom=1))
    assert result.blocks == (block,)


@pytest.mark.parametrize("width", [0, -1, float("nan"), float("inf")])
def test_invalid_page_dimensions_are_rejected(width):
    with pytest.raises(ValueError):
        select_region(replace(page(), width=width), PageRegion(x0=0, top=0, x1=1, bottom=1))


def test_evidence_scales_with_page_not_display_pixels():
    original = page()
    scaled = replace(original, width=1200, height=1600, blocks=tuple(
        replace(b, bbox=BoundingBox(b.bbox.x0 * 2, b.bbox.top * 2, b.bbox.x1 * 2, b.bbox.bottom * 2))
        for b in original.blocks
    ))
    region = PageRegion(x0=0.09, top=0.09, x1=0.21, bottom=0.14)
    assert select_region(original, region).text == select_region(scaled, region).text == "COIL-123"


@pytest.mark.parametrize("box", [BoundingBox(float("nan"), 0, 1, 1), BoundingBox(0, 0, 0, 1)])
def test_invalid_text_geometry_is_rejected(box):
    layout = replace(page(), blocks=(replace(page().blocks[0], bbox=box),))
    with pytest.raises(ValueError):
        select_region(layout, PageRegion(x0=0, top=0, x1=1, bottom=1))


def test_region_round_trip_does_not_clip_fractional_word_edges():
    block = replace(page().blocks[0], bbox=BoundingBox(71.31, 84.23, 131.73, 100.37))
    layout = replace(page(), blocks=(block,))
    result = select_region(layout, PageRegion.from_bbox(block.bbox, layout))
    assert result.status == "success"
    assert result.blocks == (block,)


def test_calvert_pilot_distinguishes_equal_certificate_and_coil_text_by_region():
    # Observed OCR boxes on page 2 of the pilot, visually checked against the scan.
    header = TextBlock(2, "4203023100", BoundingBox(123.84, 112.25, 180, 123.76),
                       confidence=0.999677836894989, source=PageSource.OCR)
    coil = TextBlock(2, "4203023100", BoundingBox(209.76, 447.57, 253.92, 456.2),
                     confidence=0.9980875253677368, source=PageSource.OCR)
    layout = PageLayout(2, 612, 792, 0, PageSource.OCR, blocks=(header, coil))
    result = select_region(layout, PageRegion.from_bbox(coil.bbox, layout))
    assert result.status == "success"
    assert result.blocks == (coil,)
    assert result.blocks[0].confidence == coil.confidence
