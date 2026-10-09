from __future__ import annotations

import pytest

from backend.app.certificate_parser.generic_extractor import (
    ColumnDefinition,
    GenericCertificateExtractor,
)
from backend.app.certificate_parser.vocabulary import (
    detect_scale_exponent,
    match_column_semantic,
    normalize_term,
)
from backend.app.domain.document import (
    BoundingBox,
    DocumentLayout,
    PageLayout,
    PageSource,
    TableRegion,
    TextBlock,
)


def test_scale_exponent_detection():
    assert detect_scale_exponent("C (10^-4)") == -4
    assert detect_scale_exponent("C (10⁻⁴)") == -4
    assert detect_scale_exponent("Mn (x10^-3)") == -3
    assert detect_scale_exponent("Si (10^-2)") == -2
    assert detect_scale_exponent("P (ppm)") == -4
    assert detect_scale_exponent("Al (%)") == 0
    assert detect_scale_exponent("S wt%") == 0
    assert detect_scale_exponent("Thick mm") is None


def test_column_semantic_matching():
    cat, key, exp = match_column_semantic("Coil No.")
    assert cat == "product_id"
    assert key == "product_id"

    cat, key, exp = match_column_semantic("Heat Number")
    assert cat == "heat_no"
    assert key == "heat_no"

    cat, key, exp = match_column_semantic("Espesor (mm)")
    assert cat == "dimension"
    assert key == "thickness_mm"

    cat, key, exp = match_column_semantic("Peso Neto (kg)")
    assert cat == "dimension"
    assert key == "weight_kg"

    cat, key, exp = match_column_semantic("C (10^-4)")
    assert cat == "chemistry"
    assert key == "C"
    assert exp == -4

    cat, key, exp = match_column_semantic("全铝 (10^-3)")  # Chinese Total Al
    assert cat == "chemistry"
    assert key == "Al_total"
    assert exp == -3


def test_generic_extractor_with_multilevel_header_and_ditto_marks():
    header_box = BoundingBox(50, 50, 500, 150)
    table_box = BoundingBox(50, 200, 500, 400)

    blocks = (
        TextBlock(1, "FABRICANTE: ACEROS NACIONALES S.A.", BoundingBox(50, 60, 300, 75)),
        TextBlock(1, "CERTIFICADO NO: CERT-8899", BoundingBox(50, 80, 250, 95)),
        TextBlock(1, "NORMA: ASTM A36", BoundingBox(50, 100, 200, 115)),
        TextBlock(1, "FECHA: 2026-08-15", BoundingBox(50, 120, 200, 135)),
    )

    # Table with 2-level header:
    # Row 0: Group labels
    # Row 1: Columns
    # Row 2: Coil 1
    # Row 3: Coil 2 with ditto marks
    table_rows = (
        ("IDENTIFICACION", None, "DIMENSIONES", None, "COMPOSICION QUIMICA (10^-2)", None, None),
        ("ROLLO", "COLADA", "ESPESOR", "ANCHO", "C", "MN", "SI"),
        ("R-001", "H-991", "2.50", "1200", "18", "65", "20"),
        ("R-002", "H-991", '"', '"', "18", "65", "20"),
    )
    table = TableRegion(1, table_box, table_rows)
    page = PageLayout(1, 612, 792, 0, PageSource.DIGITAL, blocks=blocks, tables=(table,))
    doc = DocumentLayout("unknown_mill.pdf", "hash_test", (page,))

    extractor = GenericCertificateExtractor()
    result = extractor.extract(doc)

    assert result.is_valid_certificate is True
    assert result.certificate is not None

    cert = result.certificate
    assert cert["document"]["certificate_no"] == "CERT-8899"
    assert cert["document"]["supplier"] == "ACEROS NACIONALES S.A."
    assert cert["standard"] == "ASTM A36"

    products = cert["products"]
    assert len(products) == 2

    # Product 1
    p1 = products[0]
    assert p1["product_id"] == "R-001"
    assert p1["heat_no"] == "H-991"
    assert p1["thickness_mm"] == 2.50
    assert p1["width_mm"] == 1200.0
    # 18 * 10^-2 = 0.18 %
    assert p1["composition_pct"]["C"] == 0.18
    assert p1["composition_pct"]["Mn"] == 0.65
    assert p1["composition_pct"]["Si"] == 0.20

    # Product 2 (inherited dimensions from Product 1)
    p2 = products[1]
    assert p2["product_id"] == "R-002"
    assert p2["heat_no"] == "H-991"
    assert p2["thickness_mm"] == 2.50
    assert p2["width_mm"] == 1200.0
    assert p2["observations"]["thickness_mm"]["inherited"] is True


def test_generic_extractor_preserves_unmapped_blocks():
    blocks = (
        TextBlock(1, "NOTA DE CALIDAD: MATERIAL CONFORME A REQUISITOS", BoundingBox(50, 500, 400, 520)),
        TextBlock(1, "FIRMA DE INSPECTOR: ING. LOPEZ", BoundingBox(50, 550, 300, 570)),
    )
    table = TableRegion(
        1,
        BoundingBox(50, 100, 500, 250),
        (
            ("COIL", "HEAT", "THICKNESS", "C"),
            ("C1", "H1", "1.5", "0.05"),
        ),
    )
    page = PageLayout(1, 612, 792, 0, PageSource.DIGITAL, blocks=blocks, tables=(table,))
    doc = DocumentLayout("test_unmapped.pdf", "hash_unmap", (page,))

    extractor = GenericCertificateExtractor()
    result = extractor.extract(doc)

    assert result.is_valid_certificate is True
    assert len(result.unmapped_blocks) >= 2
    unmapped_texts = [b["text"] for b in result.unmapped_blocks]
    assert any("NOTA DE CALIDAD" in t for t in unmapped_texts)
    assert any("FIRMA DE INSPECTOR" in t for t in unmapped_texts)


def test_generic_extractor_preserves_unknown_table_cells():
    table = TableRegion(
        1,
        BoundingBox(50, 100, 500, 250),
        (
            ("COIL", "HEAT", "THICKNESS", "CUSTOM TEST"),
            ("C1", "H1", "1.5", "KEEP-ME"),
        ),
    )
    page = PageLayout(1, 612, 792, 0, PageSource.DIGITAL, tables=(table,))

    result = GenericCertificateExtractor().extract(DocumentLayout("x.pdf", "hash", (page,)))

    assert result.is_valid_certificate is True
    assert any(block["text"] == "KEEP-ME" for block in result.unmapped_blocks)


def test_generic_extractor_does_not_invent_product_id_from_heat():
    table = TableRegion(
        1,
        BoundingBox(50, 100, 500, 250),
        (("HEAT", "THICKNESS"), ("H1", "6,35")),
    )
    page = PageLayout(1, 612, 792, 0, PageSource.DIGITAL, tables=(table,))

    result = GenericCertificateExtractor().extract(DocumentLayout("x.pdf", "hash", (page,)))

    assert result.is_valid_certificate is False
    assert result.certificate is None
    assert any(block["text"] == "H1" for block in result.unmapped_blocks)


def test_generic_extractor_parses_decimal_comma_and_thousands_separator():
    table = TableRegion(
        1,
        BoundingBox(50, 100, 500, 250),
        (
            ("COIL", "THICKNESS", "WIDTH", "YIELD STRENGTH"),
            ("C1", "6,35", "1,500", "280"),
        ),
    )
    page = PageLayout(1, 612, 792, 0, PageSource.DIGITAL, tables=(table,))

    result = GenericCertificateExtractor().extract(DocumentLayout("x.pdf", "hash", (page,)))

    assert result.certificate is not None
    product = result.certificate["products"][0]
    assert product["thickness_mm"] == 6.35
    assert product["width_mm"] == 1500.0
    assert product["mechanical_properties"]["yield_strength_mpa"] == 280.0


@pytest.mark.parametrize("mark", ['"', "〃", "“", "”", "″", "ditto"])
def test_ditto_does_not_cross_heat_or_table_and_preserves_original(mark):
    rows = (("Coil", "Heat", "Thickness mm", "Width mm", "C 10^-2"),
            ("AA-1", "H1", "1.8", "895", "33"),
            ("AA-2", "H1", mark, mark, mark),
            ("AA-3", "H2", mark, mark, mark),
            ("AA-4", "H2", "", "", ""),
            ("AA-5", "H2", mark, mark, mark))
    table = TableRegion(1, BoundingBox(0, 0, 500, 300), rows)
    result = GenericCertificateExtractor().extract(DocumentLayout("new.pdf", "hash", (
        PageLayout(1, 600, 800, 0, PageSource.DIGITAL, tables=(table,)),)))
    assert result.certificate is not None
    products = result.certificate["products"]
    assert products[1]["thickness_mm"] == 1.8
    assert products[1]["observations"]["thickness_mm"]["raw_value"] == mark
    assert products[1]["observations"]["thickness_mm"]["inherited_from"] == "AA-1"
    assert products[2]["thickness_mm"] == 1.8
    assert products[2]["composition_pct"] == {}
    assert len(products) == 5
    assert products[3]["thickness_mm"] is None
    assert products[4]["thickness_mm"] is None
    second = TableRegion(1, BoundingBox(0, 400, 500, 600), (rows[0], ("BB-1", "H2", mark, mark, "22")))
    result = GenericCertificateExtractor().extract(DocumentLayout("new.pdf", "hash", (
        PageLayout(1, 600, 800, 0, PageSource.DIGITAL, tables=(table, second)),)))
    assert result.certificate["products"][-1]["thickness_mm"] is None


def test_metadata_separates_dates_and_finds_description_in_notes():
    blocks = (
        TextBlock(1, "Manufacturer: Another Steel Corporation", BoundingBox(10, 20, 400, 30)),
        TextBlock(1, "SHIPPING DATE: ON/ABOUT JUN. 28, 2026", BoundingBox(10, 40, 400, 50)),
        TextBlock(1, "ISSUE DATE: JUN. 12, 2026", BoundingBox(10, 60, 400, 70)),
        TextBlock(1, "HOT ROLLED SHEET-COIL (MILL EDGE)", BoundingBox(10, 650, 400, 670)),
    )
    extractor = GenericCertificateExtractor()
    metadata = extractor._extract_metadata(DocumentLayout("unseen.pdf", "hash", (
        PageLayout(1, 600, 800, 0, PageSource.DIGITAL, blocks),)))
    assert metadata["issue_date"] == "JUN. 12, 2026"
    assert metadata["shipping_date"] == "ON/ABOUT JUN. 28, 2026"
    assert metadata["supplier"] == "Another Steel Corporation"
    assert metadata["product_name"] == "HOT ROLLED SHEET-COIL (MILL EDGE)"
    assert metadata["field_evidence"]["product_name"][0]["bbox"]["top"] == 650


def test_ambiguous_metadata_stays_unknown_with_both_sources():
    blocks = tuple(TextBlock(1, text, BoundingBox(10, y, 400, y + 10)) for text, y in (
        ("Issue date: 2026-06-12", 20), ("Issue date: 2026-06-13", 50)))
    metadata = GenericCertificateExtractor()._extract_metadata(DocumentLayout("new.pdf", "hash", (
        PageLayout(1, 600, 800, 0, PageSource.DIGITAL, blocks),)))
    assert metadata["issue_date"] is None
    assert len(metadata["field_evidence"]["issue_date"]) == 2


def test_metadata_accepts_vertical_labels_and_notes_on_another_page():
    pages = (PageLayout(1, 600, 800, 0, PageSource.DIGITAL, (
        TextBlock(1, "Issue date", BoundingBox(10, 20, 100, 30)),
        TextBlock(1, "2026-06-12", BoundingBox(10, 32, 100, 42)),)),
        PageLayout(2, 600, 800, 0, PageSource.DIGITAL, (
            TextBlock(2, "HOT-ROLLED STEEL COIL", BoundingBox(10, 650, 400, 670)),)))
    metadata = GenericCertificateExtractor()._extract_metadata(DocumentLayout("vertical.pdf", "hash", pages))
    assert metadata["issue_date"] == "2026-06-12"
    assert metadata["product_name"] == "HOT-ROLLED STEEL COIL"
    assert metadata["field_evidence"]["product_name"][0]["page_number"] == 2
