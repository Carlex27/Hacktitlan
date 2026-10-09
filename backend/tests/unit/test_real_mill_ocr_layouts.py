"""Regression snapshots of OCR produced from the user's four actual PDFs."""

import json
from pathlib import Path

import pytest

from backend.app.application.certificate_extraction import CertificateExtractionService
from backend.app.domain.document import BoundingBox, DocumentLayout, PageLayout, PageSource, TextBlock


def read_snapshot(number):
    path = Path(__file__).parents[1] / 'fixtures' / 'ocr_layouts' / f'molino-{number}.json'
    data = json.loads(path.read_text(encoding='utf-8'))
    pages = tuple(PageLayout(
        page['page_number'], page['width'], page['height'], page['rotation'], PageSource(page['source']),
        tuple(TextBlock(block['page_number'], block['text'], BoundingBox(**block['bbox']), block['confidence'], PageSource(block['source'])) for block in page['blocks']),
    ) for page in data['pages'])
    return DocumentLayout(data['file_name'], data['sha256'], pages)


@pytest.mark.parametrize('number,count,first_id,weight', [
    (1, 6, '25BH2B7550200', 7910),
    (2, 1, '263W220590210', 8995),
    (3, 11, '14159481', 7280),
    (4, 6, 'CBG2629A', 5360),
])
def test_real_pdf_ocr_produces_products_without_supplier_specific_adapters(number, count, first_id, weight):
    class Reader:
        def read(self, _path, **_kwargs):
            return read_snapshot(number)

    result = CertificateExtractionService(Reader()).analyze_pdf('snapshot.pdf')
    products = result['certificate']['products']
    assert len(products) == count
    assert products[0]['product_id'] == first_id
    assert (products[0]['weight_kg'] or products[0]['net_weight_kg']) == weight
    if number != 1:
        assert result['adapter'] == 'generic_layout_extractor'
        assert result['status'] == 'needs_review'
    if number == 2:
        assert products[0]['thickness_mm'] == 1.71
        assert products[0]['width_mm'] == 1220
        assert products[0]['gross_weight_kg'] == 9075
        assert products[0]['composition_pct']['Mn'] == .34
    if number == 3:
        assert sum(p['weight_kg'] for p in products) == 80320
        assert products[0]['label_no'] == 'T137278'
        assert products[0]['mechanical_properties']['tensile_strength_mpa'] == 546
    if number == 4:
        assert sum(p['weight_kg'] for p in products) == 34050
        assert products[0]['coating']['superior_g_m2'] == 19.1
        assert products[0]['composition_pct']['C'] == .0136
