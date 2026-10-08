from __future__ import annotations

import pytest

from backend.app.domain.document import BoundingBox
from backend.app.infrastructure.ocr.geometry import (
    clamp_bbox,
    fallback_full_page_bbox,
    normalize_points_to_bbox,
    transform_bbox_rotation,
)


def test_fallback_full_page_bbox():
    box = fallback_full_page_bbox(612.0, 792.0)
    assert box.x0 == 0.0
    assert box.top == 0.0
    assert box.x1 == 612.0
    assert box.bottom == 792.0


def test_clamp_bbox_within_boundaries():
    box = BoundingBox(10.0, 20.0, 700.0, 900.0)
    clamped = clamp_bbox(box, 612.0, 792.0)
    assert clamped.x0 == 10.0
    assert clamped.top == 20.0
    assert clamped.x1 == 612.0
    assert clamped.bottom == 792.0


def test_transform_bbox_rotation_zero_degrees():
    box = BoundingBox(10.0, 20.0, 100.0, 200.0)
    transformed = transform_bbox_rotation(box, 0, 612.0, 792.0)
    assert transformed == box


def test_transform_bbox_rotation_90_degrees_clockwise():
    # Page width=612, height=792
    # 90° clockwise maps (x, y) -> (height - y, x)
    box = BoundingBox(10.0, 20.0, 100.0, 200.0)
    transformed = transform_bbox_rotation(box, 90, 612.0, 792.0)
    # y ranges from 20 to 200, so new x ranges from 792 - 200 = 592 to 792 - 20 = 772
    # x ranges from 10 to 100, so new y ranges from 10 to 100
    assert transformed.x0 == 592.0
    assert transformed.x1 == 772.0
    assert transformed.top == 10.0
    assert transformed.bottom == 100.0


def test_transform_bbox_rotation_180_degrees():
    box = BoundingBox(10.0, 20.0, 100.0, 200.0)
    transformed = transform_bbox_rotation(box, 180, 612.0, 792.0)
    # (x, y) -> (612 - x, 792 - y)
    # new x: 612 - 100 = 512 to 612 - 10 = 602
    # new y: 792 - 200 = 592 to 792 - 20 = 772
    assert transformed.x0 == 512.0
    assert transformed.x1 == 602.0
    assert transformed.top == 592.0
    assert transformed.bottom == 772.0


def test_transform_bbox_rotation_270_degrees():
    box = BoundingBox(10.0, 20.0, 100.0, 200.0)
    transformed = transform_bbox_rotation(box, 270, 612.0, 792.0)
    # (x, y) -> (y, 612 - x)
    # new x: 20 to 200
    # new y: 612 - 100 = 512 to 612 - 10 = 602
    assert transformed.x0 == 20.0
    assert transformed.x1 == 200.0
    assert transformed.top == 512.0
    assert transformed.bottom == 602.0


def test_normalize_points_to_bbox_with_scaling():
    # Raster image is 1224 x 1584, PDF page is 612 x 792 (scale = 0.5)
    raw_polygon = [[20, 40], [200, 40], [200, 100], [20, 100]]
    box = normalize_points_to_bbox(
        raw_polygon,
        page_width=612.0,
        page_height=792.0,
        image_width=1224.0,
        image_height=1584.0,
    )
    assert box.x0 == 10.0
    assert box.top == 20.0
    assert box.x1 == 100.0
    assert box.bottom == 50.0


def test_normalize_points_empty_uses_fallback():
    box = normalize_points_to_bbox([], page_width=500.0, page_height=600.0)
    assert box.x0 == 0.0
    assert box.top == 0.0
    assert box.x1 == 500.0
    assert box.bottom == 600.0
