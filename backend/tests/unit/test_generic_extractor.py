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
