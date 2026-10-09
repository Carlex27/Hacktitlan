from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from PIL import Image
import pdfplumber
import pytest

from backend.app.document_ingestion.page_image import render_page_image
from backend.app.document_ingestion.pdf_reader import PdfPlumberReader


@pytest.mark.parametrize("number", [0, -1, 2])
def test_renderer_does_not_resolve_invalid_pages_to_another_page(monkeypatch, number):
    pdf = MagicMock()
    pdf.__enter__.return_value.pages = [object()]
    monkeypatch.setattr(pdfplumber, "open", lambda path: pdf)
    with pytest.raises(ValueError, match="Página fuera"):
        render_page_image("fake.pdf", number)


@pytest.mark.parametrize("width,height,origin,message", [
    (612, 792, (1, 0), "Origen"), (10000, 10000, (0, 0), "demasiado grande"),
])
def test_renderer_rejects_incompatible_origins_and_oversized_pages(monkeypatch, width, height, origin, message):
    pdf = MagicMock()
    pdf.__enter__.return_value.pages = [SimpleNamespace(width=width, height=height,
        bbox=(*origin, width, height))]
    monkeypatch.setattr(pdfplumber, "open", lambda path: pdf)
    with pytest.raises(ValueError, match=message):
        render_page_image("fake.pdf", 1)


def test_real_pdf_image_dimensions_match_reader_coordinates():
    path = Path(__file__).parents[3] / "data/ligie/chapter-72/source-provided/LIGIE-UNIFICADA-ACERO.pdf"
    with pdfplumber.open(path) as pdf:
        page = PdfPlumberReader()._read_page(pdf.pages[0], 1)
    image = Image.open(BytesIO(render_page_image(path, 1, expected_size=(page.width, page.height))))
    assert abs(image.width - page.width * 120 / 72) <= 1
    assert abs(image.height - page.height * 120 / 72) <= 1
    rotated = Image.open(BytesIO(render_page_image(path, 1, rotation=90, expected_size=(page.height, page.width))))
    assert rotated.size == (image.height, image.width)
