"""Re-read aligned cells when OCR merges adjacent columns into one text line."""

from dataclasses import replace
import re

from backend.app.certificate_parser.layout_rows import center, recover_rows
from backend.app.certificate_parser.vocabulary import match_column_semantic
from backend.app.domain.document import BoundingBox, PageLayout, TextBlock, PageSource


def split_headers(blocks):
    result = []
    for block in blocks:
        parts = re.findall(r'Y\.S\.|T\.S\.|Cu|Ni', block.text)
        if len(parts) > 1 and ''.join(parts).replace('.', '') == block.text.replace('.', '').replace(' ', ''):
            for index, part in enumerate(parts):
                width = (block.bbox.x1 - block.bbox.x0) / len(parts)
                result.append(replace(block, text=part, bbox=BoundingBox(block.bbox.x0 + index * width, block.bbox.top, block.bbox.x0 + (index + 1) * width, block.bbox.bottom)))
        else:
            result.append(block)
    return result


def refine_cells(page: PageLayout, image, recognizer, min_confidence: float) -> PageLayout:
    import cv2

    page = replace(page, blocks=tuple(split_headers(page.blocks)))
    rows, _ = recover_rows(page)
    anchors = [next(e for e in row['evidence'] if e['field_path'] == 'product_id')['bbox'] for row in rows]
    if len(anchors) < 2:
        return page
    ys = [(box['top'] + box['bottom']) / 2 for box in anchors]
    first_y = min(box['top'] for box in anchors)
    columns = {}
    for block in page.blocks:
        category, key, _ = match_column_semantic(block.text)
        if category == 'product_id':
            key = f'product_id:{center(block)[0]}'
            key = next((existing for existing, previous in columns.items() if existing.startswith('product_id:') and abs(center(previous)[0] - center(block)[0]) < page.width * .02), key)
        if block.text.strip().upper() == 'SAMPLE ID.':
            key = 'sample_id'
        if key and first_y - page.height * .12 < center(block)[1] < first_y:
            if key not in columns or center(block)[1] > center(columns[key])[1]:
                columns[key] = block
    xs = sorted({center(b)[0] for b in columns.values()})
    product_columns = [b for key, b in columns.items() if key.startswith('product_id:')]
    heat_column = columns.get('heat_no')
    if heat_column and any(abs(center(b)[0] - center(heat_column)[0]) < page.width * .02 for b in product_columns):
        return page
    merged = [b for b in page.blocks if b.bbox.top >= first_y and sum(b.bbox.x0 < x < b.bbox.x1 for x in xs) >= 2]
    if not merged:
        return page
    crops, boxes = [], []
    image_h, image_w = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    ink = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY_INV)[1]
    vertical = cv2.morphologyEx(ink, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(20, image_h // 12))))
    projection = (vertical > 0).sum(axis=0)
    line_pixels = [index for index, count in enumerate(projection) if count > image_h * .12]
    groups = []
    for pixel in line_pixels:
        if not groups or pixel - groups[-1][-1] > 3:
            groups.append([pixel])
        else:
            groups[-1].append(pixel)
    rulers = [sum(group) / len(group) * page.width / image_w for group in groups]
    for x_index, x in enumerate(xs):
        left = (xs[x_index - 1] + x) / 2 if x_index else min(b.bbox.x0 for b in columns.values() if center(b)[0] == x)
        right = (x + xs[x_index + 1]) / 2 if x_index + 1 < len(xs) else max(b.bbox.x1 for b in columns.values() if center(b)[0] == x) + 2
        left_rulers = [ruler for ruler in rulers if ruler < x]
        right_rulers = [ruler for ruler in rulers if ruler > x]
        if left_rulers and right_rulers:
            ruled_left, ruled_right = max(left_rulers), min(right_rulers)
            if ruled_right - ruled_left < (right - left) * 1.8:
                left, right = ruled_left + .5, ruled_right - .5
        for index, y in enumerate(ys):
            step = ys[1] - ys[0] if index == 0 else y - ys[index - 1]
            top = (ys[index - 1] + y) / 2 if index else y - step / 2
            bottom = (y + ys[index + 1]) / 2 if index + 1 < len(ys) else y + step / 2
            x0, x1 = int(left * image_w / page.width), int(right * image_w / page.width)
            y0, y1 = int(top * image_h / page.height), int(bottom * image_h / page.height)
            crop = image[max(0, y0):min(image_h, y1), max(0, x0):min(image_w, x1)]
            if crop.size:
                crops.append(cv2.resize(crop, None, fx=3, fy=3))
                boxes.append(BoundingBox(left, top, right, bottom))
    additions = []
    for box, result in zip(boxes, recognizer(crops)):
        score = float(result.get('rec_score', 0))
        text = str(result.get('rec_text', '')).strip()
        if text and (score >= min_confidence or (text in {'"', '〃'} and score >= .2)):
            additions.append(TextBlock(page.page_number, text, box, score, PageSource.OCR))
    # Keep originals as audit evidence; cell readings precede merged lines for selection.
    return replace(page, blocks=tuple(additions) + page.blocks)
