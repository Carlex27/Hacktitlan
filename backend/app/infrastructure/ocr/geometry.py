"""Unified page coordinate system, geometry normalization, rotation, and bounding boxes."""

from __future__ import annotations

from typing import Any, Sequence

from backend.app.domain.document import BoundingBox


def fallback_full_page_bbox(width: float, height: float) -> BoundingBox:
    """Return a full-page bounding box as fallback when no geometry exists."""
    return BoundingBox(0.0, 0.0, max(0.0, float(width)), max(0.0, float(height)))


def clamp_bbox(bbox: BoundingBox, max_width: float, max_height: float) -> BoundingBox:
    """Clamp bounding box within page boundaries."""
    x0 = max(0.0, min(float(bbox.x0), float(max_width)))
    top = max(0.0, min(float(bbox.top), float(max_height)))
    x1 = max(x0, min(float(bbox.x1), float(max_width)))
    bottom = max(top, min(float(bbox.bottom), float(max_height)))
    return BoundingBox(round(x0, 2), round(top, 2), round(x1, 2), round(bottom, 2))


def transform_bbox_rotation(
    bbox: BoundingBox,
    rotation_degrees: int,
    page_width: float,
    page_height: float,
) -> BoundingBox:
    """Transform bounding box coordinates when a page is rotated.

    Coordinates represent points in PDF points with top-left origin (0, 0).
    Rotations are clockwise angles (0, 90, 180, 270).
    """
    normalized_rot = rotation_degrees % 360
    if normalized_rot == 0:
        return bbox

    pts = [
        (bbox.x0, bbox.top),
        (bbox.x1, bbox.top),
        (bbox.x1, bbox.bottom),
        (bbox.x0, bbox.bottom),
    ]

    transformed_pts: list[tuple[float, float]] = []
    for x, y in pts:
        if normalized_rot == 90:
            # 90° clockwise: (x, y) -> (page_height - y, x)
            transformed_pts.append((page_height - y, x))
        elif normalized_rot == 180:
            # 180°: (x, y) -> (page_width - x, page_height - y)
            transformed_pts.append((page_width - x, page_height - y))
        elif normalized_rot == 270:
            # 270° clockwise (90° counter-clockwise): (x, y) -> (y, page_width - x)
            transformed_pts.append((y, page_width - x))
        else:
            transformed_pts.append((x, y))

    x0 = min(p[0] for p in transformed_pts)
    top = min(p[1] for p in transformed_pts)
    x1 = max(p[0] for p in transformed_pts)
    bottom = max(p[1] for p in transformed_pts)

    max_w = page_height if normalized_rot in (90, 270) else page_width
    max_h = page_width if normalized_rot in (90, 270) else page_height
    return clamp_bbox(BoundingBox(x0, top, x1, bottom), max_w, max_h)


def normalize_points_to_bbox(
    points: Sequence[Any],
    page_width: float,
    page_height: float,
    image_width: float | None = None,
    image_height: float | None = None,
    rotation: int = 0,
) -> BoundingBox:
    """Normalize raw OCR polygon/rectangle points to canonical page coordinates."""
    if not points:
        return fallback_full_page_bbox(page_width, page_height)

    # Convert flat list [x0, top, x1, bottom] if provided
    if len(points) == 4 and not isinstance(points[0], (list, tuple)):
        x0, top, x1, bottom = map(float, points)
        raw_pts = [(x0, top), (x1, bottom)]
    else:
        raw_pts = [(float(p[0]), float(p[1])) for p in points]

    min_x = min(p[0] for p in raw_pts)
    min_y = min(p[1] for p in raw_pts)
    max_x = max(p[0] for p in raw_pts)
    max_y = max(p[1] for p in raw_pts)

    # Scale from raster image pixels to page points if dimensions are provided
    if image_width and image_height and image_width > 0 and image_height > 0:
        scale_x = page_width / image_width
        scale_y = page_height / image_height
        min_x *= scale_x
        max_x *= scale_x
        min_y *= scale_y
        max_y *= scale_y

    bbox = BoundingBox(min_x, min_y, max_x, max_y)
    if rotation:
        bbox = transform_bbox_rotation(bbox, rotation, page_width, page_height)

    return clamp_bbox(bbox, page_width, page_height)
