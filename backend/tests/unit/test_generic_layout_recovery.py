from backend.app.application.certificate_extraction import CertificateExtractionService
from backend.app.certificate_parser.adapters import AdapterRegistry
from backend.app.certificate_parser.generic_extractor import GenericCertificateExtractor
from backend.app.domain.document import BoundingBox, DocumentLayout, PageLayout, PageSource, TextBlock
from backend.app.infrastructure.ocr.reader import _TableParser
from backend.app.infrastructure.ocr.table_refinement import split_headers


def block(text, x, y):
    return TextBlock(1, text, BoundingBox(x - 10, y - 3, x + 10, y + 3), .91, PageSource.OCR)


def test_unknown_supplier_without_recognized_table_recovers_rows_and_evidence():
    blocks = [block("Fabricante: NUEVO PROVEEDOR", 100, 20)]
    for text, x in (("Product No.", 50), ("Heat No.", 100), ("Size", 150), ("Weight kg", 200), ("C (%)", 250)):
        blocks.append(block(text, x, 100))
    for y, identifier, carbon in ((120, "ZZ-123", "0.05"), (140, "ZZ-456", "0.06")):
        for text, x in ((identifier, 50), ("HT-12", 100), ("1.2x900xC", 150), ("4,500", 200), (carbon, 250)):
            blocks.append(block(text, x, y))
    document = DocumentLayout("unseen.pdf", "hash", (PageLayout(1, 400, 600, 0, PageSource.OCR, tuple(blocks)),))
    result = GenericCertificateExtractor().extract(document)
    assert result.certificate is not None
    products = result.certificate["products"]
    assert [p["product_id"] for p in products] == ["ZZ-123", "ZZ-456"]
    assert products[0]["width_mm"] == 900
    assert products[0]["weight_kg"] == 4500
    assert products[0]["composition_pct"]["C"] == .05
    assert products[0]["observations"]["composition_pct"]["C"]["confidence"] == .91
    assert products[0]["observations"]["thickness_mm"]["bbox"]


def test_known_supplier_without_adapter_uses_generic_extractor():
    class Reader:
        def read(self, _path, **_kwargs):
            blocks = (block("BENGANG SAE1010MOD COLD ROLLED STEEL STRIP E02604270139", 100, 20), block("Product No.", 50, 100), block("Thickness", 150, 100), block("X-123", 50, 120), block("1.71", 150, 120))
            return DocumentLayout("known.pdf", "hash", (PageLayout(1, 400, 600, 0, PageSource.OCR, blocks),))
    result = CertificateExtractionService(Reader(), adapters=AdapterRegistry()).analyze_pdf("known.pdf")
    assert result["adapter"] == "generic_layout_extractor"
    assert result["certificate"]["products"][0]["thickness_mm"] == 1.71
    assert result["status"] == "needs_review"


def test_html_rowspan_and_colspan_keep_columns_aligned():
    parser = _TableParser()
    parser.feed('<table><tr><th rowspan="2">Coil No.</th><th colspan="2">Size</th></tr><tr><th>Thickness</th><th>Width</th></tr><tr><td>X-1</td><td>2</td><td>900</td></tr></table>')
    assert parser.rows == [("Coil No.", "Size", "Size"), ("Coil No.", "Thickness", "Width"), ("X-1", "2", "900")]


def test_merged_mechanical_headers_are_split_with_geometry():
    headers = split_headers([block("Y.S.T.S.", 100, 100)])
    assert [b.text for b in headers] == ["Y.S.", "T.S."]
    assert headers[0].bbox.x1 == headers[1].bbox.x0


def test_unknown_length_stays_unknown_and_bad_numeric_values_do_not_discard_product():
    from backend.app.domain.document import TableRegion

    table = TableRegion(1, BoundingBox(0, 0, 200, 200), (("Coil No.", "Thickness", "Width"), ("X-001", "illegible", "900")))
    result = GenericCertificateExtractor().extract(DocumentLayout("unknown.pdf", "hash", (PageLayout(1, 400, 600, 0, PageSource.DIGITAL, tables=(table,)),)))
    product = result.certificate["products"][0]
    assert product["thickness_mm"] is None
    assert product["width_mm"] == 900
    assert product["coiled"] is None
    assert any(item["text"] == "illegible" for item in result.unmapped_blocks)
