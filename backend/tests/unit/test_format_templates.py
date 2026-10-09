from dataclasses import replace

import pytest
from pydantic import ValidationError

from backend.app.certificate_parser.templates import TemplateConfiguration, preview_template
from backend.app.domain.document import BoundingBox, DocumentLayout, PageLayout, PageSource, TableRegion, TextBlock

REGION = {"x0": 0, "top": 0, "x1": 1, "bottom": 1}


def layout(rows=None):
    table = TableRegion(1, BoundingBox(10, 10, 90, 90), tuple(tuple(row) for row in (rows or [
        ["Coil", "Heat", "Thickness", "C"], ["R1", "H1", "0.1", "13"],
        ["R2", "H2", "0.2", "0"],
    ])))
    return DocumentLayout("example.pdf", "a" * 64, (PageLayout(1, 100, 100, 0, PageSource.DIGITAL, tables=(table,)),))


def configuration():
    return TemplateConfiguration.model_validate({"tables": [{"page_number": 1, "region": REGION,
        "columns": [{"target": "product_id", "header": "Coil"},
                    {"target": "heat_no", "header": "Heat"},
                    {"target": "thickness_mm", "header": "Thickness", "unit": "in"},
                    {"target": "chemistry", "element": "C", "header": "C", "unit": "%", "exponent": -4}]}]})


def test_variable_rows_units_scales_zero_and_original_values():
    result = preview_template(layout(), configuration())
    assert result.status == "success"
    products = result.certificate["products"]
    assert len(products) == 2
    assert products[0]["thickness_mm"] == 2.54
    assert products[0]["observations"]["thickness_mm"]["raw_value"] == "0.1"
    assert products[0]["composition_pct"] == {"C": .0013}
    assert products[1]["composition_pct"] == {"C": 0}
    assert products[0]["coiled"] is None and products[0]["form"] is None
    assert products[0]["evidence"][0]["product_id"] == "R1"


def test_missing_cell_is_unknown_and_requires_review():
    result = preview_template(layout([["Coil", "Heat", "Thickness", "C"], ["R1", "H1", None, None]]), configuration())
    assert result.status == "needs_review"
    assert result.certificate["products"][0]["thickness_mm"] is None
    assert result.certificate["products"][0]["composition_pct"]["C"] is None


@pytest.mark.parametrize("text", ["NaN", "inf", "-2", "0,114", "1e2000"])
def test_invalid_chemistry_never_becomes_a_number(text):
    result = preview_template(layout([["Coil", "Heat", "Thickness", "C"], ["R1", "H1", ".1", text]]), configuration())
    assert result.status == "needs_review"
    assert result.certificate["products"][0]["composition_pct"]["C"] is None


def test_decimal_comma_is_explicit():
    config = configuration().model_dump()
    config["tables"][0]["columns"][-1].update(decimal_separator=",", exponent=0)
    result = preview_template(layout([["Coil", "Heat", "Thickness", "C"], ["R1", "H1", ".1", "0,114"]]),
                              TemplateConfiguration.model_validate(config))
    assert result.certificate["products"][0]["composition_pct"]["C"] == .114


def test_conflicting_explicit_unit_is_reviewed():
    result = preview_template(layout([["Coil", "Heat", "Thickness", "C"], ["R1", "H1", "2 mm", "13"]]), configuration())
    assert any(d.code == "unit_conflict" for d in result.diagnostics)
    assert result.certificate["products"][0]["thickness_mm"] is None


def test_duplicate_identifiers_reject_normalization_without_guessing():
    result = preview_template(layout([["Coil", "Heat", "Thickness", "C"],
                                     ["R1", "H1", ".1", "13"], ["R1", "H1", ".2", "14"]]), configuration())
    assert result.status == "needs_review" and result.certificate is None
    assert any(d.code == "normalization_failed" for d in result.diagnostics)


@pytest.mark.parametrize("source,status", [(PageSource.UNREADABLE, "needs_ocr")])
def test_unreadable_page_does_not_extract(source, status):
    doc = layout()
    assert preview_template(replace(doc, pages=(replace(doc.pages[0], source=source),)), configuration()).status == status


def test_empty_draft_and_nonexistent_pages():
    assert preview_template(layout(), TemplateConfiguration()).status == "empty"
    config = configuration().model_dump()
    config["tables"][0]["page_number"] = 3
    result = preview_template(layout(), TemplateConfiguration.model_validate(config))
    assert result.status == "needs_review" and result.diagnostics[0].code == "page_missing"


def test_partial_table_and_missing_header_require_review():
    config = configuration().model_dump()
    config["tables"][0]["region"]["x1"] = .5
    assert preview_template(layout(), TemplateConfiguration.model_validate(config)).diagnostics[0].code == "clipped_table"
    result = preview_template(layout([["Wrong", "Heat", "Thickness", "C"], ["R1", "H1", ".1", "13"]]), configuration())
    assert result.diagnostics[0].code == "header_ambiguous"


def test_shared_chemistry_joins_by_heat_not_row_order():
    doc = layout([["Coil", "Heat"], ["R1", "H1"], ["R2", "H1"], ["R3", "H2"]])
    chemistry = TableRegion(2, BoundingBox(10, 10, 90, 90), (("Heat", "C"), ("H2", "20"), ("H1", "10")))
    doc = replace(doc, pages=(*doc.pages, PageLayout(2, 100, 100, 0, PageSource.DIGITAL, tables=(chemistry,))))
    config = {"tables": [
        {"page_number": 1, "region": REGION, "columns": [{"target": "product_id", "header": "Coil"},
                                                          {"target": "heat_no", "header": "Heat"}]},
        {"page_number": 2, "region": REGION, "role": "chemistry", "join_key": "heat_no",
         "columns": [{"target": "heat_no", "header": "Heat"},
                     {"target": "chemistry", "element": "C", "header": "C", "unit": "%", "exponent": -2}]},
    ]}
    result = preview_template(doc, TemplateConfiguration.model_validate(config))
    assert result.status == "success"
    assert [p["composition_pct"]["C"] for p in result.certificate["products"]] == [.1, .1, .2]
    changed = replace(chemistry, rows=(("Heat", "C"), ("H1", "20"), ("H1", "10")))
    result = preview_template(replace(doc, pages=(doc.pages[0], replace(doc.pages[1], tables=(changed,)))),
                              TemplateConfiguration.model_validate(config))
    assert result.status == "needs_review"
    assert {d.code for d in result.diagnostics} >= {"join_ambiguous", "join_missing"}


def test_schema_rejects_unknown_fields_units_and_duplicate_targets():
    with pytest.raises(ValidationError):
        TemplateConfiguration.model_validate({"execute": "anything"})
    config = configuration().model_dump()
    config["tables"][0]["columns"][2]["unit"] = "kg"
    with pytest.raises(ValidationError):
        TemplateConfiguration.model_validate(config)
    config = configuration().model_dump()
    config["tables"][0]["columns"].append(config["tables"][0]["columns"][0])
    with pytest.raises(ValidationError):
        TemplateConfiguration.model_validate(config)


def test_individual_fields_preserve_confidence_and_clipping():
    page = PageLayout(1, 100, 100, 0, PageSource.OCR, blocks=(
        TextBlock(1, "R1", BoundingBox(10, 10, 30, 20), .72, PageSource.OCR),))
    doc = DocumentLayout("one.pdf", "a" * 64, (page,))
    config = TemplateConfiguration.model_validate({"fields": [{"target": "product_id", "page_number": 1, "region": REGION}]})
    result = preview_template(doc, config)
    assert result.status == "success" and result.evidence[0]["blocks"][0]["confidence"] == .72
    config = config.model_dump()
    config["fields"][0]["region"]["x1"] = .2
    result = preview_template(doc, TemplateConfiguration.model_validate(config))
    assert result.status == "needs_review" and result.certificate is None


def test_mechanical_evidence_does_not_mix_rolls_in_the_same_heat():
    doc = layout([["Coil", "Heat"], ["R1", "H1"], ["R2", "H1"]])
    mechanical = TableRegion(2, BoundingBox(10, 10, 90, 90), (("Coil", "Yield"), ("R2", "300"), ("R1", "200")))
    doc = replace(doc, pages=(*doc.pages, PageLayout(2, 100, 100, 0, PageSource.DIGITAL, tables=(mechanical,))))
    config = TemplateConfiguration.model_validate({"tables": [
        {"page_number": 1, "region": REGION, "columns": [{"target": "product_id", "header": "Coil"},
                                                          {"target": "heat_no", "header": "Heat"}]},
        {"page_number": 2, "region": REGION, "role": "mechanical", "join_key": "product_id",
         "columns": [{"target": "product_id", "header": "Coil"},
                     {"target": "yield_strength_mpa", "header": "Yield", "unit": "MPa"}]},
    ]})
    result = preview_template(doc, config)
    assert result.status == "success"
    first, second = result.certificate["products"]
    assert first["mechanical_properties"]["yield_strength_mpa"] == 200
    assert second["mechanical_properties"]["yield_strength_mpa"] == 300
    assert all(item.get("product_id") in (None, "R1") for item in first["evidence"])
    assert [e["raw_value"] for e in first["evidence"] if e["field"] == "yield_strength_mpa"] == ["200"]


def test_aliases_cannot_duplicate_normalized_chemistry_columns():
    config = configuration().model_dump()
    config["tables"][0]["columns"][-1].update(element="Al", header="Al")
    config["tables"][0]["columns"].append({"target": "chemistry", "element": "Al_total",
                                           "header": "Total", "unit": "%", "exponent": 0})
    with pytest.raises(ValidationError):
        TemplateConfiguration.model_validate(config)


def test_unmapped_pages_are_reported_instead_of_omitting_other_products():
    doc = layout()
    doc = replace(doc, pages=(*doc.pages, replace(doc.pages[0], page_number=2)))
    result = preview_template(doc, configuration())
    assert result.status == "needs_review"
    assert any(d.code == "page_not_mapped" and d.page_number == 2 for d in result.diagnostics)


def test_shared_chemistry_without_a_relationship_key_is_rejected():
    config = configuration().model_dump()
    config["fields"] = [{"target": "chemistry", "element": "C", "exponent": 0,
                         "unit": "%", "page_number": 1, "region": REGION}]
    with pytest.raises(ValidationError):
        TemplateConfiguration.model_validate(config)
