import unittest

from backend.app.certificate_parser.detection import DocumentKind, detect_document_kind
from backend.app.certificate_parser.semantics import (
    discover_field_candidates,
    discover_table_candidates,
    identify_field,
)
from backend.app.domain.document import (
    BoundingBox,
    DocumentLayout,
    PageLayout,
    PageSource,
    TableRegion,
    TextBlock,
)


def layout_with(*texts: str, tables: tuple[TableRegion, ...] = ()) -> DocumentLayout:
    blocks = tuple(
        TextBlock(1, text, BoundingBox(0, index * 10, 100, index * 10 + 8))
        for index, text in enumerate(texts)
    )
    page = PageLayout(1, 612, 792, 0, PageSource.DIGITAL, blocks, tables)
    return DocumentLayout("sample.pdf", "abc", (page,))


class DocumentDetectionTests(unittest.TestCase):
    def test_detects_unseen_certificate_from_semantic_signals(self):
        document = layout_with(
            "ACME MILL TEST CERTIFICATE",
            "HEAT NO   COIL NO",
            "CHEMICAL COMPOSITION",
            "THICKNESS WIDTH WEIGHT",
        )

        result = detect_document_kind(document)

        self.assertEqual(result.kind, DocumentKind.MILL_CERTIFICATE)
        self.assertEqual(result.confidence, 1.0)
        self.assertIn("product-identifiers", result.signals)

    def test_does_not_accept_an_unrelated_invoice(self):
        document = layout_with("COMMERCIAL INVOICE", "CUSTOMER", "TOTAL AMOUNT")

        result = detect_document_kind(document)

        self.assertEqual(result.kind, DocumentKind.UNKNOWN)
        self.assertEqual(result.confidence, 0.0)

    def test_spanish_and_supplier_variants_map_to_canonical_fields(self):
        self.assertEqual(identify_field("Número de colada")[0], "heat_no")
        self.assertEqual(identify_field("ESPESOR (mm)")[0], "thickness_mm")
        self.assertEqual(identify_field("Cast No.")[0], "heat_no")

    def test_dynamic_table_headers_are_discovered_without_fixed_positions(self):
        table = TableRegion(
            1,
            BoundingBox(10, 100, 600, 400),
            (
                ("COIL NO.", "HEAT NO.", "THICK", "WIDTH", "MASS kg"),
                ("A1", "H1", "1.8", "895", "7280"),
                ("A2", "H1", '"', '"', "7310"),
            ),
        )
        document = layout_with("INSPECTION CERTIFICATE", tables=(table,))

        candidate = discover_table_candidates(document)[0]
        fields = set(candidate.columns.values())

        self.assertEqual(candidate.row_count, 2)
        self.assertTrue({"product_id", "heat_no", "thickness_mm", "width_mm"} <= fields)
        self.assertIn("heat_no", {item.field for item in discover_field_candidates(document)})


if __name__ == "__main__":
    unittest.main()

