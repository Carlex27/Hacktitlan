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
    ('4-refined', 6, 'CBG2629A', 5360),
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
        assert result['certificate']['document']['product_name'] == 'Cold-rolled steel strip'
        assert products[0]['label_no'] == first_id
        assert products[0]['thickness_mm'] == 1.71
        assert products[0]['width_mm'] == 1220
        assert products[0]['gross_weight_kg'] == 9075
        assert products[0]['composition_pct']['Mn'] == .34
    if number == 3:
        assert sum(p['weight_kg'] for p in products) == 80320
        assert products[0]['label_no'] == 'T137278'
        assert products[0]['mechanical_properties']['tensile_strength_mpa'] == 546
    if number in (4, '4-refined'):
        assert sum(p['weight_kg'] for p in products) == 34050
        metadata = result['certificate']['document']
        assert metadata['product_name'] == 'EG COIL(ZN)'
        assert metadata['supplier'] == 'GOLDEN STATE CORPORATION'
        assert metadata['customer'] == 'H&K INTERNATIONAL LIMITED'
        assert [p['heat_no'] for p in products] == ['SB06562'] * 3 + ['SB05270'] * 3
        for index, product in enumerate(products):
            assert product['standard'] == 'SECC'
            assert product['composition_pct'] == (
                {'C': .0136, 'Si': .020, 'Mn': .116, 'P': .0090, 'S': .0061}
                if index < 3 else
                {'C': .0142, 'Si': .022, 'Mn': .127, 'P': .0102, 'S': .0054}
            )
        assert products[0]['coating']['superior_g_m2'] == 19.1
        assert products[0]['composition_pct']['C'] == .0136


def test_real_metadata_snapshot_finds_notes_and_does_not_mix_shipping_with_issue():
    from backend.app.certificate_parser.generic_extractor import GenericCertificateExtractor
    result = GenericCertificateExtractor().extract(read_snapshot(3))
    metadata = result.certificate["document"]
    assert metadata["supplier"] == "CHINA STEEL CORPORATION"
    assert metadata["customer"] == "HANWA CO., LTD."
    assert metadata["issue_date_raw"] == "JUN 12, 2026"
    assert "JUN 28" in metadata["shipping_date_raw"]
    assert "ABOUT" in metadata["shipping_date_raw"]
    assert metadata["product_name"] == "HOT ROLLED SHEET-COIL (MILL EDGE)"


def test_molino3_refined_cells_preserve_all_elements_and_repeated_dimensions():
    from backend.app.certificate_parser.generic_extractor import GenericCertificateExtractor
    certificate = GenericCertificateExtractor().extract(read_snapshot('3-refined')).certificate
    products = certificate['products']
    assert len(products) == 11
    assert [p['heat_no'] for p in products] == ['3VL99'] * 2 + ['1FN43'] * 9
    expected = {'C': .35, 'Mn': .63, 'P': .017, 'S': .001, 'Si': .2,
                'Cu': .01, 'Ni': .01, 'Cr': .01, 'Al_total': .019,
                'B': .0003, 'Mo': 0, 'N': .004}
    for index, product in enumerate(products):
        chemistry = expected if index < 2 else {**expected, 'C': .33, 'Mn': .64,
                     'P': .016, 'S': .002, 'Si': .18, 'Al_total': .025, 'B': .0002}
        assert product['composition_pct'] == chemistry
        assert (product['thickness_mm'], product['width_mm']) == (1.8, 895)
        assert (product['standard'], product['grade']) == ('SAE 1035', '1035')
        if index not in (0, 2):
            assert product['observations']['composition_pct']['C']['inherited']


def test_molino3_prefers_original_33_and_retains_conflicting_39():
    class Reader:
        def read(self, _path, **_kwargs):
            return read_snapshot(3)
    result = CertificateExtractionService(Reader()).analyze_pdf("snapshot.pdf")
    carbon = result["certificate"]["products"][2]["observations"]["composition_pct"]["C"]
    assert carbon["raw_value"] == "33" and carbon["normalized_value"] == .33
    assert carbon["verification"]["raw_value"] == "39"
    assert carbon["verification"]["normalized_value"] == .39
    assert carbon["verification"]["header_text"] == "C 10^-2"
    assert carbon["verification"]["error_code"] == "conflicting_ocr_readings"
    assert result["status"] == "needs_review"


@pytest.mark.parametrize("mode", ["neighbor", "inherited", "multiple"])
def test_ocr_comparison_does_not_pick_an_unjustified_correction(mode):
    from dataclasses import replace
    from backend.app.certificate_parser.generic_extractor import GenericCertificateExtractor
    from backend.app.infrastructure.ollama_verification import reconcile_ocr_readings
    layout = read_snapshot(3)
    certificate = GenericCertificateExtractor().extract(layout).certificate
    carbon = certificate["products"][2]["observations"]["composition_pct"]["C"]
    carbon.update(raw_value="39", normalized_value=.39)
    block = next(b for b in layout.pages[0].blocks if b.text == "33" and b.bbox.x0 > 500)
    if mode == "inherited":
        carbon["inherited"] = True
    elif mode == "neighbor":
        shifted = replace(block, bbox=BoundingBox(block.bbox.x0, block.bbox.top + 20, block.bbox.x1, block.bbox.bottom + 20))
        page = replace(layout.pages[0], blocks=tuple(shifted if b is block else b for b in layout.pages[0].blocks))
        layout = replace(layout, pages=(page,))
    else:
        page = replace(layout.pages[0], blocks=layout.pages[0].blocks + (replace(block, text="32"),))
        layout = replace(layout, pages=(page,))
    reconcile_ocr_readings(layout, certificate)
    assert carbon["normalized_value"] == .39
    assert carbon.get("verification", {}).get("status") != "discrepancy"
