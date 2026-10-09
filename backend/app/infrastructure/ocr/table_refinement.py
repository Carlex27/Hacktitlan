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


def is_ditto_image(crop) -> bool:
    """Recognize two short printed strokes, without treating a numeral 1 as repetition."""
    import cv2

    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    ink = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY_INV)[1]
    height, width = ink.shape
    vertical = cv2.morphologyEx(ink, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, height)))
    horizontal = cv2.morphologyEx(ink, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (width, 1)))
    ink = cv2.subtract(ink, cv2.bitwise_or(vertical, horizontal))
    ink[:2] = ink[-2:] = 0
    ink[:, :2] = ink[:, -2:] = 0
    _, _, stats, _ = cv2.connectedComponentsWithStats(ink)
    strokes = [s for s in stats[1:] if s[4] >= 3]
    if len(strokes) != 2:
        return False
    left, right = sorted(strokes, key=lambda s: s[0])
    return bool(all(2 <= s[3] <= height * .55 and s[2] <= s[3] for s in strokes)
                and abs(left[1] - right[1]) <= 2
                and abs(left[3] - right[3]) <= 2
                and 0 < right[0] - left[0] <= width * .5)


def refine_cells(page: PageLayout, image, recognizer, min_confidence: float) -> PageLayout:
    import cv2

    page = replace(page, blocks=tuple(split_headers(page.blocks)))
    rows, scales = recover_rows(page)
    anchors = [next(e for e in row['evidence'] if e['field_path'] == 'product_id')['bbox'] for row in rows]
    if not anchors:
        return page
    ys = [(box['top'] + box['bottom']) / 2 for box in anchors]
    first_y = min(box['top'] for box in anchors)
    chemical_ys = sorted(center(b)[1] for b in page.blocks
                         if b.text.strip() in {'C', 'Mn', 'Si', 'P'}
                         and first_y - page.height * .12 < center(b)[1] < first_y)
    chemical_y = chemical_ys[len(chemical_ys) // 2] if chemical_ys else None
    if len(anchors) == 1 and chemical_y is None:
        return page
    columns = {}
    for block in page.blocks:
        category, key, _ = match_column_semantic(block.text)
        if category == 'chemistry' and chemical_y is not None and abs(center(block)[1] - chemical_y) > page.height * .02:
            continue
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
    if len(anchors) > 1 and heat_column and any(abs(center(b)[0] - center(heat_column)[0]) < page.width * .02 for b in product_columns):
        return page
    merged = [b for b in page.blocks if b.bbox.top >= first_y and sum(b.bbox.x0 < x < b.bbox.x1 for x in xs) >= 2]
    if not merged and len(anchors) > 1:
        return page
    crops, boxes, dittos = [], [], []
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
    header_additions = []
    for key, block in columns.items():
        if match_column_semantic(block.text)[0] != 'chemistry' or key in scales:
            continue
        top = block.bbox.bottom
        bottom = min(first_y, top + page.height * .035)
        y0, y1 = int(top * image_h / page.height), int(bottom * image_h / page.height)
        band = ink[y0:y1]
        if band.size == 0:
            continue
        boundaries = [i * page.width / image_w for i, count in enumerate((band > 0).sum(axis=0))
                      if count >= band.shape[0] * .85]
        x = center(block)[0]
        lefts, rights = [v for v in boundaries if v < x], [v for v in boundaries if v > x]
        if not lefts or not rights:
            continue
        left, right = max(lefts) + .5, min(rights) - .5
        crop = image[y0:y1, int(left * image_w / page.width):int(right * image_w / page.width)]
        if not crop.size:
            continue
        crop = _without_cell_rules(crop)
        result = next(iter(recognizer([cv2.resize(crop, None, fx=4, fy=4)])))
        text = str(result.get('rec_text', '')).strip()
        if not re.search(r'10\s*[-−^]?[1-6]', text):
            mask = cv2.threshold(cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY), 180, 255, cv2.THRESH_BINARY_INV)[1]
            for shape in ((mask.shape[1], 1), (1, mask.shape[0])):
                mask = cv2.subtract(mask, cv2.morphologyEx(mask, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, shape)))
            _, _, components, _ = cv2.connectedComponentsWithStats(mask)
            powers = [s for s in components[1:] if s[4] >= 5 and s[2] >= 2 and s[3] >= 4
                      and s[0] > mask.shape[1] * .45 and s[1] + s[3] / 2 < mask.shape[0] * .65]
            if powers:
                px, py, pw, ph, _ = min(powers, key=lambda s: s[1])
                power_crop = crop[py:py + ph, px:px + pw]
                power_crop = cv2.copyMakeBorder(power_crop, 4, 4, 4, 4, cv2.BORDER_CONSTANT, value=(255, 255, 255))
                power = next(iter(recognizer([cv2.resize(power_crop, None, fx=6, fy=6)])))
                digit = str(power.get('rec_text', '')).strip()
                base = next(iter(recognizer([cv2.resize(crop[py + ph:], None, fx=4, fy=4)])))
                if '10' in str(base.get('rec_text', '')) and re.fullmatch(r'[1-6]', digit) and float(power.get('rec_score', 0)) >= min_confidence:
                    text = f'X10^-{digit}'
        if text and float(result.get('rec_score', 0)) >= min_confidence:
            header_additions.append(TextBlock(page.page_number, text, BoundingBox(left, top, right, bottom),
                                              float(result['rec_score']), PageSource.OCR))
    for x_index, x in enumerate(xs):
        if len(anchors) == 1 and not any(center(block)[0] == x and match_column_semantic(block.text)[0] == 'chemistry' for block in columns.values()):
            continue
        left = (xs[x_index - 1] + x) / 2 if x_index else min(b.bbox.x0 for b in columns.values() if center(b)[0] == x)
        right = (x + xs[x_index + 1]) / 2 if x_index + 1 < len(xs) else max(b.bbox.x1 for b in columns.values() if center(b)[0] == x) + 2
        left_rulers = [ruler for ruler in rulers if ruler < x]
        right_rulers = [ruler for ruler in rulers if ruler > x]
        if left_rulers and right_rulers:
            ruled_left, ruled_right = max(left_rulers), min(right_rulers)
            if ruled_right - ruled_left < (right - left) * 1.8:
                left, right = ruled_left + .1, ruled_right - .1
        for index, y in enumerate(ys):
            step = page.height * .035 if len(ys) == 1 else ys[1] - ys[0] if index == 0 else y - ys[index - 1]
            top = (ys[index - 1] + y) / 2 if index else y - step / 2
            bottom = (y + ys[index + 1]) / 2 if index + 1 < len(ys) else y + step / 2
            x0, x1 = int(left * image_w / page.width), int(right * image_w / page.width)
            y0, y1 = int(top * image_h / page.height), int(bottom * image_h / page.height)
            crop = image[max(0, y0):min(image_h, y1), max(0, x0):min(image_w, x1)]
            if crop.size:
                crop = crop.copy()
                dark = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) < 180
                for edge in (range(min(3, crop.shape[1])), range(max(0, crop.shape[1] - 3), crop.shape[1])):
                    for pixel in edge:
                        if dark[:, pixel].mean() > .95:
                            crop[:, pixel] = 255
                crops.append(cv2.resize(crop, None, fx=3, fy=3))
                boxes.append(BoundingBox(left, top, right, bottom))
                dittos.append(is_ditto_image(crop))
    additions = []
    for box, result, ditto in zip(boxes, recognizer(crops), dittos):
        score = float(result.get('rec_score', 0))
        text = str(result.get('rec_text', '')).strip()
        if ditto:
            text, score = '"', 1.0
        if text and (score >= min_confidence or (text in {'"', '〃'} and score >= .2)):
            additions.append(TextBlock(page.page_number, text, box, score, PageSource.OCR))
    # Keep originals as audit evidence; cell readings precede merged lines for selection.
    return replace(page, blocks=tuple(header_additions) + tuple(additions) + page.blocks)


def _without_cell_rules(crop):
    """Remove full cell borders that interfere with small digits and superscripts."""
    import cv2

    ink = cv2.threshold(cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY), 180, 255, cv2.THRESH_BINARY_INV)[1]
    horizontal = cv2.morphologyEx(ink, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (crop.shape[1], 1)))
    lines = cv2.bitwise_or(horizontal, cv2.morphologyEx(ink, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, crop.shape[0]))))
    cleaned = crop.copy()
    cleaned[lines > 0] = 255
    return cv2.copyMakeBorder(cleaned, 4, 4, 4, 4, cv2.BORDER_CONSTANT, value=(255, 255, 255))
