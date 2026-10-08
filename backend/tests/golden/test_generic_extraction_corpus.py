from __future__ import annotations

import json
from pathlib import Path

from backend.app.application.certificate_extraction import (
    CertificateExtractionService,
    ExtractionStatus,
)
from backend.app.domain.document import (
    BoundingBox,
    DocumentLayout,
    PageLayout,
    PageSource,
    TableRegion,
    TextBlock,
)

SAMPLES_DIR = Path(__file__).parents[3] / "data" / "samples"


class FakeReader:
    def __init__(self, doc: DocumentLayout):
        self.doc = doc

    def read(self, _path):
        return self.doc


def layout_from_raw_fixture(raw: dict) -> DocumentLayout:
    metadata = raw["document"]
    blocks = (
        TextBlock(1, f"FABRICANTE: {metadata['supplier']}", BoundingBox(50, 40, 450, 55)),
        TextBlock(1, f"CERTIFICADO NO: {metadata['certificate_no']}", BoundingBox(50, 60, 350, 75)),
        TextBlock(1, f"NORMA: {raw['standard']}", BoundingBox(50, 80, 350, 95)),
    )
    chemistry = list(raw["chemistry_scales"])
    headers = [
        "COIL",
        "HEAT",
        "THICKNESS",
        "WIDTH",
        "LENGTH",
        "WEIGHT",
        "YIELD STRENGTH",
        "TENSILE STRENGTH",
        "ELONGATION",
        *[
            f"{element} ({'%' if raw['chemistry_scales'][element] == 0 else raw['chemistry_scales'][element]})"
            for element in chemistry
        ],
    ]
    rows = [headers]
    for item in raw["rows"]:
        rows.append(
            [
                item["product_id"],
                item["heat_no"],
                item["thickness_mm"],
                item["width_mm"],
                item.get("length_m", item.get("length_raw")),
                item["weight_kg"],
                item["yield_strength_mpa"],
                item["tensile_strength_mpa"],
                item["elongation_pct"],
                *[item["chemistry"][element] for element in chemistry],
            ]
        )
    table = TableRegion(
        1,
        BoundingBox(50, 150, 550, 350),
        tuple(tuple(None if value is None else str(value) for value in row) for row in rows),
    )
    page = PageLayout(1, 612, 792, 0, PageSource.DIGITAL, blocks=blocks, tables=(table,))
    return DocumentLayout(metadata["source_name"], "fixture-hash", (page,))


def test_corpus_desconocido_1_placa_normalization():
    raw_path = SAMPLES_DIR / "desconocido-1-placa.raw.json"
    raw = json.loads(raw_path.read_text(encoding="utf-8"))

    extraction = CertificateExtractionService(FakeReader(layout_from_raw_fixture(raw))).analyze_pdf(
        "ignored.pdf"
    )
    assert extraction["status"] == ExtractionStatus.NEEDS_REVIEW.value
    normalized = extraction["certificate"]
    products = normalized["products"]

    assert len(products) == 2
    assert products[0]["product_id"] == "PL-101"
    assert products[0]["heat_no"] == "COL-5510"
    assert products[0]["thickness_mm"] == 6.35
    assert products[0]["width_mm"] == 1500.0
    assert products[0]["length_m"] == 6.0
    assert products[0]["weight_kg"] == 4485.0
    assert products[0]["standard"] == "ASTM A36"

    # Exact chemistry
    chem = products[0]["composition_pct"]
    assert chem["C"] == 0.18
    assert chem["Si"] == 0.22
    assert chem["Mn"] == 0.75
    assert chem["P"] == 0.018
    assert chem["S"] == 0.012

    # Mechanical properties
    props = products[0]["mechanical_properties"]
    assert props["yield_strength_mpa"] == 280.0
    assert props["tensile_strength_mpa"] == 440.0
    assert props["elongation_pct"] == 26.5


def test_corpus_desconocido_2_multilevel_scale_normalization():
    raw_path = SAMPLES_DIR / "desconocido-2-multinivel.raw.json"
    raw = json.loads(raw_path.read_text(encoding="utf-8"))

    extraction = CertificateExtractionService(FakeReader(layout_from_raw_fixture(raw))).analyze_pdf(
        "ignored.pdf"
    )
    assert extraction["status"] == ExtractionStatus.NEEDS_REVIEW.value
    normalized = extraction["certificate"]
    products = normalized["products"]

    assert len(products) == 3
    assert normalized["validation"]["piece_count_matches"] is True

    p0 = products[0]
    assert p0["product_id"] == "EG-8801"
    assert p0["heat_no"] == "H-7741"
    assert p0["thickness_mm"] == 3.0
    assert p0["width_mm"] == 1250.0
    assert p0["coiled"] is True

    # Chemical scaling: 15 * 10^-2 = 0.15%, 25 * 10^-3 = 0.025%
    chem = p0["composition_pct"]
    assert chem["C"] == 0.15
    assert chem["Si"] == 0.20
    assert chem["Mn"] == 0.60
    assert chem["P"] == 0.014
    assert chem["S"] == 0.006
    assert chem["Al_total"] == 0.025


def test_unknown_document_ingestion_end_to_end_sets_needs_review_with_candidate_certificate():
    blocks = (
        TextBlock(1, "FABRICANTE: LAMINADORA CENTRAL S.A.", BoundingBox(50, 40, 350, 55)),
        TextBlock(1, "CERTIFICADO NO: LC-2026-0045", BoundingBox(50, 60, 250, 75)),
        TextBlock(1, "NORMA: SAE 1020", BoundingBox(50, 80, 200, 95)),
        TextBlock(1, "OBSERVACION: INSPECCION VISUAL SATISFACTORIA", BoundingBox(50, 450, 400, 465)),
    )
    table_rows = (
        ("ROLLO", "COLADA", "ESPESOR mm", "ANCHO mm", "C %", "MN %", "SI %"),
        ("R-100", "C-882", "4.50", "1220", "0.20", "0.45", "0.15"),
        ("R-101", "C-882", "4.50", "1220", "0.20", "0.45", "0.15"),
    )
    table = TableRegion(1, BoundingBox(50, 150, 500, 300), table_rows)
    page = PageLayout(1, 612, 792, 0, PageSource.DIGITAL, blocks=blocks, tables=(table,))
    doc = DocumentLayout("unknown_supplier.pdf", "hash_end_to_end", (page,))

    service = CertificateExtractionService(FakeReader(doc))
    result = service.analyze_pdf("ignored.pdf")

    # Must be needs_review because it's an unknown format
    assert result["status"] == ExtractionStatus.NEEDS_REVIEW.value
    assert result["adapter"] == "generic_layout_extractor"
    assert "certificate" in result
    assert result["certificate"] is not None

    products = result["certificate"]["products"]
    assert len(products) == 2
    assert products[0]["product_id"] == "R-100"
    assert products[0]["thickness_mm"] == 4.50
    assert products[0]["composition_pct"]["C"] == 0.20

    # Unmapped blocks preserved for review
    assert "unmapped_blocks" in result
    assert any("INSPECCION VISUAL SATISFACTORIA" in b["text"] for b in result["unmapped_blocks"])


def test_unknown_document_insufficient_material_data_does_not_fabricate_products():
    # Only header metadata without tables or material properties
    blocks = (
        TextBlock(1, "MILL TEST CERTIFICATE", BoundingBox(50, 40, 250, 55)),
        TextBlock(1, "INVOICE / FACTURA: INV-9912", BoundingBox(50, 60, 250, 75)),
        TextBlock(1, "GENERAL NOTES: PENDING PRODUCTION DISPATCH", BoundingBox(50, 80, 350, 95)),
    )
    page = PageLayout(1, 612, 792, 0, PageSource.DIGITAL, blocks=blocks, tables=())
    doc = DocumentLayout("invoice_not_cert.pdf", "hash_inv", (page,))

    service = CertificateExtractionService(FakeReader(doc))
    result = service.analyze_pdf("ignored.pdf")

    assert result["status"] in {
        ExtractionStatus.NEEDS_REVIEW.value,
        ExtractionStatus.UNSUPPORTED.value,
    }
    assert "certificate" not in result or result["certificate"] is None
    assert "reasons" in result
    assert any("No se pudieron segmentar" in r for r in result["reasons"])


def test_unknown_document_partial_certificate_signals_falls_into_needs_review():
    # Has certificate signals and coil id but missing table material data
    blocks = (
        TextBlock(1, "MILL TEST CERTIFICATE", BoundingBox(50, 40, 250, 55)),
        TextBlock(1, "COIL NO: LC-9988", BoundingBox(50, 60, 200, 75)),
        TextBlock(1, "GENERAL NOTES: PENDING MECHANICAL LAB TESTS", BoundingBox(50, 80, 350, 95)),
    )
    page = PageLayout(1, 612, 792, 0, PageSource.DIGITAL, blocks=blocks, tables=())
    doc = DocumentLayout("partial_cert.pdf", "hash_partial", (page,))

    service = CertificateExtractionService(FakeReader(doc))
    result = service.analyze_pdf("ignored.pdf")

    assert result["status"] == ExtractionStatus.NEEDS_REVIEW.value
    assert "certificate" not in result or result["certificate"] is None
    assert "reasons" in result
    assert any("No se pudieron segmentar" in r for r in result["reasons"])
