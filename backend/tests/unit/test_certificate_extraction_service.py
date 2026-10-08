import json
from pathlib import Path
import unittest

from backend.app.application.certificate_extraction import CertificateExtractionService
from backend.app.domain.document import (
    BoundingBox,
    DocumentLayout,
    PageLayout,
    PageSource,
    TextBlock,
)


FIXTURE = Path(__file__).parents[3] / "data" / "samples" / "molino-1.raw.json"


class FakeReader:
    def __init__(self, document: DocumentLayout) -> None:
        self.document = document

    def read(self, path):
        return self.document


def document(source: PageSource, *texts: str) -> DocumentLayout:
    blocks = tuple(
        TextBlock(1, text, BoundingBox(0, index * 10, 100, index * 10 + 8), source=source)
        for index, text in enumerate(texts)
    )
    page = PageLayout(1, 612, 792, 0, source, blocks)
    return DocumentLayout("unknown-layout.pdf", "abc123", (page,))


class CertificateExtractionServiceTests(unittest.TestCase):
    def test_unknown_certificate_is_sent_to_review_without_inventing_products(self):
        layout = document(
            PageSource.DIGITAL,
            "MILL TEST CERTIFICATE",
            "COIL NO HEAT NO",
            "CHEMICAL COMPOSITION THICKNESS",
        )

        result = CertificateExtractionService(FakeReader(layout)).analyze_pdf("ignored.pdf")

        self.assertEqual(result["status"], "needs_review")
        self.assertEqual(result["detection"]["kind"], "mill_certificate")
        self.assertNotIn("certificate", result)
        self.assertTrue(result["field_candidates"])

    def test_image_only_document_requests_ocr(self):
        layout = document(PageSource.UNREADABLE)

        result = CertificateExtractionService(FakeReader(layout)).analyze_pdf("ignored.pdf")

        self.assertEqual(result["status"], "needs_ocr")

    def test_existing_normalization_path_is_preserved(self):
        raw = json.loads(FIXTURE.read_text(encoding="utf-8"))

        result = CertificateExtractionService.normalize_known_payload(raw)

        self.assertEqual(len(result["products"]), 6)
        self.assertEqual(result["products"][0]["composition_pct"]["C"], 0.0013)

    def test_known_profile_without_registered_adapter_fails_closed(self):
        layout = document(
            PageSource.DIGITAL,
            "BX STEEL POSCO BTA BLZ112 COLD ROLLED STEEL STRIP E02511200001",
        )

        result = CertificateExtractionService(FakeReader(layout)).analyze_pdf("ignored.pdf")

        self.assertEqual(result["status"], "needs_review")
        self.assertEqual(result["profile"]["name"], "MOLINO_1_BX_POSCO")
        self.assertNotIn("certificate", result)
        self.assertIn("no tiene un adaptador registrado", result["reasons"][0])


if __name__ == "__main__":
    unittest.main()
