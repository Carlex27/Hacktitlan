import unittest

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
