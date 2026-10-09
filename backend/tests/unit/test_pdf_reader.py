import unittest
from hashlib import sha256
from unittest.mock import MagicMock, patch

import pytest

from backend.app.document_ingestion.pdf_reader import PdfPlumberReader
from backend.app.domain.document import PageSource


class FakePage:
    width = 612
    height = 792
    rotation = 0

    def __init__(self, tokens):
        self.tokens = tokens

    def extract_words(self, **kwargs):
        return [
            {"text": token, "x0": index, "top": 0, "x1": index + 1, "bottom": 1}
            for index, token in enumerate(self.tokens)
        ]

    def find_tables(self):
        return []


class PdfReaderTests(unittest.TestCase):
    def test_fragmented_scan_text_layer_still_requires_ocr(self):
        page = FakePage(list("BENGANGSTEELPLATESCOLTD"))

        result = PdfPlumberReader()._read_page(page, 1)

        self.assertEqual(result.source, PageSource.UNREADABLE)

    def test_normal_digital_words_are_accepted(self):
        page = FakePage(["MILL", "TEST", "CERTIFICATE", "CHEMICAL", "COMPOSITION"])

        result = PdfPlumberReader()._read_page(page, 1)

        self.assertEqual(result.source, PageSource.DIGITAL)


if __name__ == "__main__":
    unittest.main()


def test_read_releases_each_page_and_preserves_layout_and_hash(tmp_path):
    path = tmp_path / "certificate.pdf"
    content = b"%PDF" + b"certificate" * 100_000
    path.write_bytes(content)
    pages = [FakePage(["MILL", "TEST", "CERTIFICATE", "CHEMICAL", "COMPOSITION"]) for _ in range(2)]
    for page in pages:
        page.close = MagicMock()
    reader = PdfPlumberReader()
    expected = tuple(reader._read_page(page, number) for number, page in enumerate(pages, 1))
    pdf = MagicMock()
    pdf.pages = pages
    pdf.metadata = {"Producer": "test"}
    with patch("pdfplumber.open") as opened:
        opened.return_value.__enter__.return_value = pdf
        result = reader.read(path)
    assert result.pages == expected
    assert result.sha256 == sha256(content).hexdigest()
    assert result.metadata == pdf.metadata
    for page in pages:
        page.close.assert_called_once_with()


def test_read_releases_page_on_extraction_error(tmp_path):
    from backend.app.document_ingestion.pdf_reader import DocumentIngestionError

    path = tmp_path / "broken.pdf"
    path.write_bytes(b"%PDF")
    page = MagicMock()
    page.extract_words.side_effect = ValueError("invalid page")
    with patch("pdfplumber.open") as opened:
        opened.return_value.__enter__.return_value.pages = [page]
        with pytest.raises(DocumentIngestionError, match="invalid page"):
            PdfPlumberReader().read(path)
    page.close.assert_called_once_with()
