import json
from pathlib import Path
import unittest

from backend.app.application.certificate_extraction import CertificateExtractionService
from backend.app.certificate_parser.adapters import AdapterRegistry
from backend.app.certificate_parser.molino_1_adapter import Molino1Adapter
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

        result = CertificateExtractionService(
            FakeReader(layout), adapters=AdapterRegistry()
        ).analyze_pdf("ignored.pdf")

        self.assertEqual(result["status"], "needs_review")
        self.assertEqual(result["detection"]["kind"], "mill_certificate")
        self.assertNotIn("certificate", result)
        self.assertTrue(result["field_candidates"])

    def test_image_only_document_requests_ocr(self):
        layout = document(PageSource.UNREADABLE)

        result = CertificateExtractionService(
            FakeReader(layout), adapters=AdapterRegistry()
        ).analyze_pdf("ignored.pdf")

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

        result = CertificateExtractionService(
            FakeReader(layout), adapters=AdapterRegistry()
        ).analyze_pdf("ignored.pdf")

        self.assertEqual(result["status"], "needs_review")
        self.assertEqual(result["profile"]["name"], "MOLINO_1_BX_POSCO")
        self.assertNotIn("certificate", result)
        self.assertIn("se intentó extracción genérica", result["reasons"][0])

    def test_molino_1_adapter_extracts_all_rows_from_ocr_geometry(self):
        raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
        blocks = [
            TextBlock(1, "BXSTEELPOSCOCOLDROLLEDSHEETCO.LTD.", BoundingBox(0, 0, 10, 10)),
            TextBlock(1, "BTA BLZ112 ASTM A1008 E02511200001", BoundingBox(0, 10, 10, 20)),
        ]
        columns = {"heat_no": 74, "thickness_mm": 108, "width_mm": 127, "length_raw": 147,
                   "net_weight_kg": 173, "gross_weight_kg": 173,
                   "C": 237, "Si": 256, "Mn": 275, "P": 294, "S": 314, "Als": 334, "Ti": 355}
        for index, row in enumerate(raw["rows"]):
            anchor = 315.5 - index * 17
            blocks.append(TextBlock(1, row["product_id"], BoundingBox(anchor - 3, 50, anchor + 3, 98)))
            values = {
                "heat_no": row["heat_no"], "thickness_mm": row["thickness_mm"],
                "width_mm": row["width_mm"], "length_raw": row["length_raw"],
                "net_weight_kg": row["net_weight_kg"], "gross_weight_kg": row["gross_weight_kg"],
                **row["chemistry"],
            }
            for key, value in values.items():
                offset = -8 if key in {"heat_no", "gross_weight_kg"} else 0
                blocks.append(TextBlock(
                    1, str(value),
                    BoundingBox(anchor + offset - 2, columns[key] - 2, anchor + offset + 2, columns[key] + 2),
                ))
            for top, offset, value in ((445, -8, 148), (464, 0, 308), (484, 0, 53)):
                blocks.append(TextBlock(1, str(value), BoundingBox(anchor + offset - 2, top - 2, anchor + offset + 2, top + 2)))
        layout = DocumentLayout(
            "MOLINO 1.pdf", "fixture",
            (PageLayout(1, 792, 612, 90, PageSource.OCR, tuple(blocks)),),
        )

        normalized = CertificateExtractionService(
            FakeReader(layout), adapters=AdapterRegistry((Molino1Adapter(),))
        ).analyze_pdf("ignored.pdf")

        self.assertEqual(normalized["status"], "extracted")
        self.assertEqual(normalized["adapter"], "MOLINO_1_BX_POSCO")
        self.assertEqual(len(normalized["certificate"]["products"]), 6)
        self.assertEqual(normalized["certificate"]["products"][0]["product_id"], "25BH2B7550200")


if __name__ == "__main__":
    unittest.main()
