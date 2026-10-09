"""Regression for the user's scanned Calvert certificate and its licensing letter."""
from dataclasses import replace
import json
from pathlib import Path

import pytest

from backend.app.application.certificate_extraction import CertificateExtractionService
from backend.app.certificate_parser.calvert_adapter import CalvertAdapter
from backend.app.certificate_parser.layout_rows import recover_rows
from backend.app.domain.document import BoundingBox, DocumentLayout, PageLayout, PageSource, TextBlock


def layout():
    data = json.loads((Path(__file__).parents[1] / "fixtures/ocr_layouts/calvert.json").read_text(encoding="utf-8"))
    pages = tuple(PageLayout(
        page["page_number"], page["width"], page["height"], page["rotation"], PageSource(page["source"]),
        tuple(TextBlock(block["page_number"], block["text"], BoundingBox(**block["bbox"]),
                        block["confidence"], PageSource(block["source"])) for block in page["blocks"]),
    ) for page in data["pages"])
    return DocumentLayout(data["file_name"], data["sha256"], pages)


def test_calvert_real_ocr_uses_coil_not_letter_standard():
    document = layout()

    class Reader:
        def read(self, *_args, **_kwargs):
            return document

    result = CertificateExtractionService(Reader()).analyze_pdf("calvert.pdf")
    assert result["adapter"] == "ARCELORMITTAL_CALVERT"
    certificate = result["certificate"]
    assert certificate["document"]["certificate_no"] == "2302380630"
    assert certificate["document"]["supplier"] == "ArcelorMittal Calvert LLC"
    assert certificate["document"]["issue_date_raw"] == "2026-06-28"
    assert certificate["standard"] == "M2021 SP221PE"
    assert len(certificate["products"]) == 1
    product = certificate["products"][0]
    assert product["product_id"] == "2302380630"
    assert product["heat_no"] == "2620689"
    assert (product["thickness_mm"], product["width_mm"]) == (1.8, 1496)
    assert (product["net_weight_kg"], product["gross_weight_kg"]) == (10000, 10000)
    assert product["weight_kg"] == 10000 and product["weight_kind"] == "net"
    assert product["rolling"] == "hot" and product["coiled"] is True
    assert product["composition_pct"] == {
        "C": .032, "Si": .015, "Mn": .25, "P": .005, "S": .002, "Al_total": .040,
        "Cr": .01, "Cu": .007, "Mo": .001, "N": .0034, "Ni": .002, "Nb": .001,
        "Ti": .002, "B": .0050, "V": .001, "Ca": .0018, "Sn": .001,
    }
    assert product["mechanical_properties"] == {
        "yield_strength_mpa": 209, "tensile_strength_mpa": 322, "elongation_pct": 47,
    }
    assert any(e["page"] == 4 and "A1011 CS-B" in e["source_text"] for e in product["evidence"])
    assert {e["page"] for e in product["evidence"]} == {2, 3, 4}


def test_generic_geometry_does_not_create_coil_from_standard_in_letter():
    assert recover_rows(layout().pages[3])[0] == []


def test_calvert_rejects_conflicting_certificate_numbers():
    document = layout()
    page = document.pages[2]
    page = replace(page, blocks=tuple(replace(block, text="9999999999")
                                     if block.text == "2302380630" else block for block in page.blocks))
    with pytest.raises(ValueError, match="ambiguo"):
        CalvertAdapter().extract(replace(document, pages=(*document.pages[:2], page, document.pages[3])))


def test_calvert_missing_measurement_is_not_zero():
    document = layout()
    page = document.pages[2]
    page = replace(page, blocks=tuple(block for block in page.blocks if block.text != "209 MPa"))
    payload = CalvertAdapter().extract(replace(document, pages=(*document.pages[:2], page, document.pages[3])))
    assert "yield_strength_mpa" not in payload["rows"][0]


def test_calvert_preserves_explicit_zero_chemistry():
    document = layout()
    page = document.pages[1]
    page = replace(page, blocks=tuple(replace(block, text="0") if block.text == "0.032" else block
                                     for block in page.blocks))
    payload = CalvertAdapter().extract(replace(document, pages=(document.pages[0], page, *document.pages[2:])))
    assert payload["rows"][0]["chemistry"]["C"] == "0"


def test_calvert_multiple_coils_do_not_share_unlabelled_tensile_tests():
    document = layout()
    page = document.pages[1]
    extra = []
    for block in page.blocks:
        if 448 <= block.bbox.top <= 449 and block.text in {"2302380630", "2620689", "10,000.000"}:
            bbox = replace(block.bbox, top=block.bbox.top + 16, bottom=block.bbox.bottom + 16)
            extra.append(replace(block, text="2302380631" if block.text == "2302380630" else block.text, bbox=bbox))
    page = replace(page, blocks=(*page.blocks, *extra))
    payload = CalvertAdapter().extract(replace(document, pages=(document.pages[0], page, *document.pages[2:])))
    assert len(payload["rows"]) == 2
    assert [row["product_id"] for row in payload["rows"]] == ["2302380630", "2302380631"]
    assert all("yield_strength_mpa" not in row for row in payload["rows"])
