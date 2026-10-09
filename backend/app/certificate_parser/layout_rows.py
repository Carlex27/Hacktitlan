"""Recover supplier-independent table rows from aligned OCR/text blocks."""

from __future__ import annotations

import re
from dataclasses import dataclass

from backend.app.certificate_parser.vocabulary import match_column_semantic, detect_scale_exponent, DITTO_TOKENS
from backend.app.domain.document import PageLayout, TextBlock
from backend.app.certificate_parser.measurement_units import dimension_value


def center(block: TextBlock) -> tuple[float, float]:
    return ((block.bbox.x0 + block.bbox.x1) / 2, (block.bbox.top + block.bbox.bottom) / 2)


@dataclass(frozen=True)
class LayoutColumn:
    block: TextBlock
    category: str
    key: str
    exponent: int | None


def recover_rows(page: PageLayout) -> tuple[list[dict], dict[str, int]]:
    columns = []
    for block in page.blocks:
        category, key, exponent = match_column_semantic(block.text)
        if key and category != 'unknown':
            columns.append(LayoutColumn(block, category, key, exponent))
    identifiers = [c for c in columns if c.category == 'product_id']
    candidates = []
    for column in identifiers:
        x, y = center(column.block)
        anchors = []
        for block in page.blocks:
            bx, by = center(block)
            if by <= column.block.bbox.bottom:
                continue
            if abs(bx - x) > max((column.block.bbox.x1 - column.block.bbox.x0) / 2, page.width * .018):
                continue
            tokens = re.findall(r'\b[A-Za-z0-9_-]*[A-Za-z][A-Za-z0-9_-]*\d[A-Za-z0-9_-]*\b|\b\d{6,}\b', block.text)
            if len(tokens) == 1 and not re.search(r'total|subtotal', block.text, re.I):
                anchors.append((block, tokens[0]))
        if anchors:
            mixed = [(b, token) for b, token in anchors if re.search(r'[A-Za-z]', token)]
            if mixed:
                anchors = mixed
            unique = []
            for block, token in anchors:
                b = block.bbox
                duplicate = next((index for index, (previous, prior_token) in enumerate(unique)
                    if prior_token == token
                    and min(b.bottom, previous.bbox.bottom) - max(b.top, previous.bbox.top)
                        >= min(b.bottom - b.top, previous.bbox.bottom - previous.bbox.top) * .5
                    and min(b.x1, previous.bbox.x1) - max(b.x0, previous.bbox.x0)
                        >= min(b.x1 - b.x0, previous.bbox.x1 - previous.bbox.x0) * .5), None)
                if duplicate is None:
                    unique.append((block, token))
                elif b.bottom - b.top < unique[duplicate][0].bbox.bottom - unique[duplicate][0].bbox.top:
                    unique[duplicate] = (block, token)
            anchors = unique
            candidates.append((column, anchors))
    if not candidates:
        return [], {}
    id_column, anchors = max(candidates, key=lambda item: (len(item[1]), bool(re.search(r'coil\s*no|product\s*no', item[0].block.text, re.I))))
    anchors.sort(key=lambda pair: center(pair[0])[1])
    first_y = min(block.bbox.top for block, _ in anchors)
    header_columns = [c for c in columns if first_y - page.height * .2 < center(c.block)[1] < first_y]
    selected = {'product_id': id_column}
    chemical_y = [center(c.block)[1] for c in header_columns if c.category == 'chemistry' and c.block.text.strip() in {'C', 'Mn', 'Si', 'P', 'Alt', 'Als'}]
    chemistry_header_y = sorted(chemical_y)[len(chemical_y) // 2] if chemical_y else None
    for column in header_columns:
        if column.category == 'product_id':
            if re.search(r'label\s*no', column.block.text, re.I) and column is not id_column:
                selected['label_no'] = LayoutColumn(column.block, 'label', 'label_no', None)
            continue
        if column.category == 'chemistry' and chemistry_header_y is not None and abs(center(column.block)[1] - chemistry_header_y) > page.height * .02:
            continue
        prior = selected.get(column.key)
        if prior is None or center(column.block)[1] > center(prior.block)[1]:
            selected[column.key] = column
    scales = {}
    for key, column in selected.items():
        if column.category != 'chemistry':
            continue
        exponent = column.exponent
        if exponent is None:
            x, y = center(column.block)
            nearby = [b for b in page.blocks if (abs(center(b)[0] - x) < page.width * .015 or b.bbox.x0 <= x <= b.bbox.x1) and y < center(b)[1] < first_y]
            exponent = next((detect_scale_exponent(b.text) for b in nearby if detect_scale_exponent(b.text) is not None), None)
            power_blocks = sorted((b for b in nearby if re.fullmatch(r'[1-6]', b.text.strip())), key=lambda b: abs(center(b)[0] - x))
            powers = [int(b.text.strip()) for b in power_blocks]
            if exponent is None and powers and any('10' in b.text for b in nearby):
                exponent = -powers[0]
            scaled_header = any(re.search(r'[x×]10|10\s*[-−]', b.text, re.I) and first_y - page.height * .1 < b.bbox.top < first_y for b in page.blocks)
            if exponent is None and not scaled_header and any('%' in b.text and b.bbox.x0 <= x <= b.bbox.x1 and first_y - page.height * .15 < b.bbox.top < first_y for b in page.blocks):
                exponent = 0
        if exponent is not None:
            scales[key] = exponent
    rows = []
    for index, (anchor, identifier) in enumerate(anchors):
        y = center(anchor)[1]
        before = center(anchors[index - 1][0])[1] if index else y - (center(anchors[1][0])[1] - y if len(anchors) > 1 else page.height * .035)
        after = center(anchors[index + 1][0])[1] if index + 1 < len(anchors) else y + (y - before)
        low, high = (before + y) / 2, (after + y) / 2
        row = {'product_id': identifier, 'chemistry': {}, 'evidence': []}
        if any(re.search(r'\bpack\s*no\b', column.block.text, re.I)
               and abs(center(column.block)[0] - center(id_column.block)[0]) < page.width * .018
               for column in header_columns):
            row['label_no'] = identifier
            row['evidence'].append({'page': page.page_number, 'field_path': 'label_no',
                                    'bbox': anchor.bbox.as_dict(), 'source_text': anchor.text,
                                    'confidence': anchor.confidence})
        for key, column in selected.items():
            if key == 'product_id':
                values = [anchor]
            else:
                x = center(column.block)[0]
                neighbors = sorted({center(c.block)[0] for c in selected.values()})
                distances = [abs(nx - x) for nx in neighbors if abs(nx - x) > page.width * .008]
                tolerance = min(distances) * .45 if distances else page.width * .025
                values = [b for b in page.blocks if low <= center(b)[1] < high and abs(center(b)[0] - x) <= tolerance and b.bbox.bottom - b.bbox.top < max(high - low, 12) * 1.8]
                values = [b for b in values if sum(b.bbox.x0 < nx < b.bbox.x1 for nx in neighbors) < 2]
                if key == 'heat_no' and abs(x - center(id_column.block)[0]) < page.width * .02:
                    values = [b for b in values if b is not anchor]
                if key == 'label_no':
                    identifiers = [b for b in values if re.fullmatch(r'\d{0,3}[A-Za-z][A-Za-z0-9_-]*\d[A-Za-z0-9_-]*', b.text.strip())]
                    if identifiers:
                        values = identifiers
                if column.category in {'dimension', 'mechanical', 'chemistry'}:
                    values = [b for b in values if b.text.strip() in DITTO_TOKENS or re.fullmatch(r'[\d.,]+|COIL|C|ROLLO|[\d.,]+[xX×*][\d.,]+[xX×*]C', b.text.strip(), re.I)
                              or (key in {'thickness_mm', 'width_mm', 'length_m'} and dimension_value(b.text, column.block.text) is not None)]
                values.sort(key=lambda b: (abs(center(b)[1] - y), abs(center(b)[0] - x)))
            if not values:
                continue
            value = values[0]
            if key == 'weight_kg' and any(re.search(r'gross|bruto|毛重', b.text, re.I) and abs(center(b)[0] - center(column.block)[0]) < page.width * .02 and first_y - page.height * .2 < b.bbox.top < first_y for b in page.blocks):
                weights = sorted((b for b in values if re.fullmatch(r'[\d.,]+', b.text.strip())), key=lambda b: b.bbox.top)
                if len(weights) == 2:
                    for weight_key, weight in zip(('net_weight_kg', 'gross_weight_kg'), weights):
                        row[weight_key] = weight.text.strip()
                        row['evidence'].append({'page': page.page_number, 'field_path': weight_key, 'bbox': weight.bbox.as_dict(), 'source_text': weight.text, 'confidence': weight.confidence})
                    value = weights[0]
            if column.category == 'chemistry' and key not in scales:
                # An unlabelled chemical scale is evidence for review, never an assumed percent.
                continue
            text = value.text.strip()
            if key == 'product_id':
                text = identifier
            elif key == 'label_no':
                text = re.sub(r'^\d{1,3}(?=[A-Za-z])', '', text)
            if column.category == 'chemistry':
                row['chemistry'][key] = text
            else:
                row[key] = text
            row['evidence'].append({'page': page.page_number, 'field_path': f'composition_pct.{key}' if column.category == 'chemistry' else key, 'bbox': value.bbox.as_dict(), 'source_text': value.text, 'confidence': value.confidence})
        row['dimension_headers'] = {key: column.block.text for key, column in selected.items() if column.category == 'dimension'}
        rows.append(row)
    return rows, scales
