from types import SimpleNamespace

import pytest

from backend.app.config import Settings
from backend.app.domain.document import PageLayout, PageSource
from backend.app.infrastructure.ocr.reader import PaddleStructureReader, is_arcelormittal_cover


@pytest.mark.parametrize('text,expected', [
    ('ArcelorMittal Calvert Inspection Document Cover Sheet', True),
    ('ArcelorMittal Calvert Inspection\nDocument Cover Sheet', True),
    ('ArcelorMittal Mill Certificate CHEMICAL COMPOSITION', False),
    ('ArcelorMittal COATING TENSILE TEST', False),
    ('Inspection Document Cover Sheet Other manufacturer', False),
    ('', False),
])
def test_cover_requires_company_and_explicit_cover_title(text, expected):
    assert is_arcelormittal_cover(text) is expected


@pytest.mark.parametrize('probe_fails', [False, True])
def test_two_certificates_skip_only_covers_and_keep_page_numbers(tmp_path, monkeypatch, probe_fails):
    import sys
    import pdfplumber
    from PIL import Image
    import numpy as np

    image = Image.new('RGB', (32, 24), 'white')
    native_images = [np.full((24, 32, 3), n, dtype=np.uint8) for n in range(6)]
    predicted = []
    rendered = []
    titles = iter(['ArcelorMittal Calvert Inspection Document Cover Sheet',
                   'ArcelorMittal Mill Certificate', 'ArcelorMittal COATING TENSILE TEST'] * 2)

    class Page:
        width, height = 612, 792
        def __init__(self, index):
            self.index = index
        def crop(self, box):
            return self
        def to_image(self, resolution, antialias=False):
            rendered.append(resolution)
            if resolution == 144:
                assert antialias is True
                return SimpleNamespace(original=Image.fromarray(native_images[self.index]))
            return SimpleNamespace(original=image)

    class Pdf:
        pages = [Page(n) for n in range(6)]
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass

    class HeaderOcr:
        def predict(self, image, **kwargs):
            if probe_fails:
                raise RuntimeError('header unavailable')
            yield {'rec_texts': [next(titles)]}

    class Pipeline:
        paddlex_pipeline = SimpleNamespace(general_ocr_pipeline=HeaderOcr())
        def predict(self, **kwargs):
            predicted.append(kwargs['input'])
            yield {'doc_preprocessor_res': {'angle': 0}, 'rec_texts': ['certificate data'],
                   'rec_scores': [1], 'rec_boxes': [[0, 0, 20, 10]]}

    monkeypatch.setattr(pdfplumber, 'open', lambda path: Pdf())
    monkeypatch.setitem(sys.modules, 'paddlex.inference.pipelines.components',
                        SimpleNamespace(rotate_image=lambda image, angle: image))
    path = tmp_path / 'scan.pdf'
    path.write_bytes(b'%PDF')
    reader = PaddleStructureReader(Settings(ocr_enabled=True), pipeline_factory=lambda **kwargs: Pipeline())
    progress = []
    results = reader._predict(path, 'cpu', total_pages=6,
                              page_callback=lambda current, total: progress.append((current, total)))
    assert [r['page_index'] + 1 for r in results if r.get('skip_cover')] == ([] if probe_fails else [1, 4])
    assert rendered.count(300) == (6 if probe_fails else 4)
    assert rendered.count(144) == rendered.count(300)
    assert rendered.count(150) == 0
    expected = native_images if probe_fails else [native_images[n] for n in (1, 2, 4, 5)]
    assert len(predicted) == len(expected)
    assert all(np.array_equal(actual, original) for actual, original in zip(predicted, expected, strict=True))
    assert progress == [(n, 6) for n in range(1, 7)]
    pages = tuple(PageLayout(n, 612, 792, 0, PageSource.UNREADABLE) for n in range(1, 7))
    converted = reader._convert_results(results, pages)
    assert list(converted) == [1, 2, 3, 4, 5, 6]
    assert all(page.source is PageSource.OCR for page in converted.values())
    if not probe_fails:
        assert not converted[1].blocks and not converted[4].blocks
    assert converted[5].blocks[0].page_number == 5

