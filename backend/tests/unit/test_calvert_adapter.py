"""Regression for the user's scanned Calvert certificate and its licensing letter."""
from dataclasses import replace
import json
from pathlib import Path

import pytest

from backend.app.application.certificate_extraction import CertificateExtractionService
from backend.app.certificate_parser.calvert_adapter import CalvertAdapter
from backend.app.certificate_parser.layout_rows import recover_rows
from backend.app.domain.document import BoundingBox, DocumentLayout, PageLayout, PageSource, TextBlock


def layout(name="calvert"):
    data = json.loads((Path(__file__).parents[1] / f"fixtures/ocr_layouts/{name}.json").read_text(encoding="utf-8"))
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


def test_calvert_bundle_keeps_chemistry_dimensions_and_tests_with_each_certificate():
    document = layout()
    first_pages = document.pages[1:3]
    second_pages = tuple(replace(page, page_number=page.page_number + 2, blocks=tuple(
        replace(block, page_number=block.page_number + 2,
                text=block.text.replace("2302380630", "4404014860").replace("2620689", "2640604")
                    .replace("Hot Roll Pickled & Oiled", "Aluminize").replace("Hot Roll Base", "Cold Roll Base").replace("1.800", "2.000")
                    .replace("0.032", "0.243").replace("209 MPa", "407 MPa"))
        for block in page.blocks)) for page in first_pages)
    bundled = replace(document, pages=(*first_pages, *second_pages))

    class Reader:
        def read(self, *_args, **_kwargs):
            return bundled

    certificate = CertificateExtractionService(Reader()).analyze_pdf("bundle.pdf")["certificate"]
    first, second = certificate["products"]
    assert certificate["document"]["certificate_no"] is None
    assert (first["product_id"], second["product_id"]) == ("2302380630", "4404014860")
    assert (first["composition_pct"]["C"], second["composition_pct"]["C"]) == (.032, .243)
    assert (first["mechanical_properties"]["yield_strength_mpa"],
            second["mechanical_properties"]["yield_strength_mpa"]) == (209, 407)
    assert second["coating"]["metal"] == "Al"
    assert second["rolling"] == "cold"
    assert (first["thickness_mm"], second["thickness_mm"]) == (1.8, 2)
    assert all(e["page"] in {4, 5} for e in second["evidence"])


def test_real_aluminize_scan_recovers_both_coils_and_all_chemical_elements():
    document = layout("calvert-aluminize")

    class Reader:
        def read(self, *_args, **_kwargs):
            return document

    result = CertificateExtractionService(Reader()).analyze_pdf("aluminize.pdf")
    assert result["adapter"] == "ARCELORMITTAL_CALVERT"
    certificate = result["certificate"]
    assert certificate["document"]["supplier"] == "ArcelorMittal Calvert LLC"
    assert certificate["document"]["issue_date_raw"] == "2026-06-28"
    first, second = certificate["products"]
    assert [(p["product_id"], p["heat_no"], p["thickness_mm"], p["width_mm"])
            for p in (first, second)] == [("4404035750", "2640998", 1.2, 1105),
                                         ("4404014860", "2640604", 2, 1073)]
    assert all(len(p["composition_pct"]) == 17 for p in (first, second))
    assert first["composition_pct"]["C"] == .220
    assert second["composition_pct"]["C"] == .213
    assert second["composition_pct"]["Si"] == .232
    assert second["composition_pct"]["Al_total"] == .033
    assert first["weight_kg"] == 20370
    assert second["net_weight_kg"] is None
    assert second["weight_kg"] == second["gross_weight_kg"] == 10090
    assert second["weight_kind"] == "gross"
    assert any(e["source_text"] == "10,090,000" for e in second["evidence"])
    assert first["mechanical_properties"] == {"yield_strength_mpa": 407, "tensile_strength_mpa": 602, "elongation_pct": 28}
    assert second["mechanical_properties"] == {"yield_strength_mpa": 417, "tensile_strength_mpa": 594, "elongation_pct": 27}
    for product, top, bottom in ((first, 46, 48), (second, 47, 46)):
        assert product["rolling"] == "cold"
        assert product["coating"]["metal"] == "Al"
        assert product["coating"]["superior_g_m2"] == top
        assert product["coating"]["inferior_g_m2"] == bottom
