from dataclasses import replace
from decimal import Decimal
from hashlib import sha256
import json
from types import SimpleNamespace

from fastapi.testclient import TestClient
import pytest

from backend.app.api.app import create_app
from backend.app.classification_engine import Chapter72ClassificationEngine, ProductFacts, StepOutcome, source_reference
from backend.app.classification_engine.catalog import SourceProvidedCatalog
from backend.app.classification_engine.engine import ALLOY_THRESHOLDS
from backend.app.classification_engine.source_evidence import SOURCE_SHA256, SOURCE_PDF, verified_source_pdf
from backend.app.config import Settings
from backend.app.application.classification_service import ClassificationService
from backend.app.application.review_service import ReviewService
from backend.app.domain.errors import ApplicationError


def product(**changes):
    chemistry = dict.fromkeys(ALLOY_THRESHOLDS, Decimal("0"))
    chemistry["C"] = Decimal("0.08")
    values = dict(product_id="audit", form="flat_rolled", coiled=True, rolling="cold",
                  width_mm=Decimal("1220"), thickness_mm=Decimal("1.7"),
                  composition_pct=chemistry, coated=False, yield_strength_mpa=Decimal("250"))
    values.update(changes)
    return ProductFacts(**values)


@pytest.mark.parametrize("element,threshold", ALLOY_THRESHOLDS.items())
@pytest.mark.parametrize("offset,expected", [("-0.00000001", "non_alloy"), ("0", "other_alloy"), ("0.00000001", "other_alloy")])
def test_every_alloy_threshold_below_at_above(element, threshold, offset, expected):
    facts = product()
    facts = replace(facts, composition_pct={**facts.composition_pct, element: threshold + Decimal(offset)})
    assert Chapter72ClassificationEngine().classify(facts).product_type == f"flat_rolled_{expected}"


def test_threshold_registry_matches_extracted_notes():
    payload = json.loads(SOURCE_PDF.with_name("classification-notes.json").read_text(encoding="utf-8"))
    # Check each percentage against the actual PDF text as well as all boundary tests.
    import pdfplumber
    with pdfplumber.open(SOURCE_PDF) as pdf:
        text = pdf.pages[6].extract_text()
    assert payload
    evidence = json.loads(SOURCE_PDF.with_name("alloy-evidence.json").read_text(encoding="utf-8"))
    assert set(evidence) == set(ALLOY_THRESHOLDS)
    for element, threshold in ALLOY_THRESHOLDS.items():
        assert f"{threshold}%" in evidence[element]["source_text"]
        assert evidence[element]["source_text"] in text


def test_missing_carbon_cannot_prove_non_alloy_steel():
    facts = product()
    result = Chapter72ClassificationEngine().classify(replace(facts, composition_pct={**facts.composition_pct, "C": None}))
    assert result.fraction is None
    assert "composition_pct.C" in result.missing_fields


@pytest.mark.parametrize("element", ["Se", "Bi", "As", "Al_soluble"])
def test_other_elements_and_soluble_aluminium_keep_original_evidence(element):
    facts = product()
    chemistry = {**facts.composition_pct, element: Decimal("0.3" if element == "Al_soluble" else "0.1")}
    if element == "Al_soluble":
        chemistry["Al_total"] = None
    result = Chapter72ClassificationEngine().classify(replace(facts, composition_pct=chemistry))
    assert result.product_type == "flat_rolled_other_alloy"
    factor = result.ranked_candidates[0].factors[0]
    assert factor.observed == {element: str(chemistry[element])}


@pytest.mark.parametrize("series,thickness,nico", [("200", "3.9", "02"), ("300", "4", "03"), ("400", "4", "04"), ("200", "4.001", "91"), ("300", "4.1", "92"), ("400", "4.7", "93")])
def test_stainless_series_and_four_mm_boundary(series, thickness, nico):
    facts = product(stainless_series=series, thickness_mm=Decimal(thickness))
    chemistry = {**facts.composition_pct, "Cr": Decimal("18"), "Ni": Decimal("8")}
    result = Chapter72ClassificationEngine().classify(replace(facts, composition_pct=chemistry))
    assert (result.fraction, result.nico) == ("72193202", nico)


def test_stainless_series_is_not_inferred_from_composition():
    facts = product()
    result = Chapter72ClassificationEngine().classify(replace(facts, composition_pct={**facts.composition_pct, "Cr": Decimal("18"), "Ni": Decimal("8")}))
    assert result.nico is None
    assert "stainless_series" in result.missing_fields
    assert len(result.ranked_candidates) == 3
    assert all(candidate.factors[-1].outcome is StepOutcome.UNKNOWN for candidate in result.ranked_candidates)


@pytest.mark.parametrize("strength,nico", [("274.999", "99"), ("275", "01"), ("354.999", "01"), ("355", "02"), ("355.001", "02")])
def test_galvanized_actual_yield_thresholds(strength, nico):
    result = Chapter72ClassificationEngine().classify(product(coated=True, coating_metal="Zn", coating_process="hot_dip", pattern_in_relief=False, yield_strength_mpa=Decimal(strength)))
    assert (result.fraction, result.nico) == ("72104999", nico)


def test_flat_rolled_sheet_geometry_is_checked():
    result = Chapter72ClassificationEngine().classify(product(coiled=False, width_mm=Decimal("10"), thickness_mm=Decimal("2")))
    assert result.fraction is None
    assert "flat_rolled_definition" in result.missing_fields


def test_titanium_evidence_and_catalog_evidence_go_to_distinct_pages():
    catalog = SourceProvidedCatalog()
    alloy = source_reference(catalog, "chapter72.definition.other_alloy", "72255091", "99", ("composition_pct.Ti",))
    assert alloy["page_number"] == 7
    assert "0.05% de titanio" in alloy["source_text"]
    assert alloy["bbox"]["y0"] < alloy["bbox"]["y1"]
    assert source_reference(catalog, "chapter72.nico.72255091.99", "72255091", "99")["page_number"] == 44
    assert source_reference(catalog, "chapter72.fraction.72255091", "72255091", "99")["page_number"] == 43
    assert source_reference(catalog, "chapter72.definition.other_alloy", source_hash="different-version") == {}


def test_bundled_source_integrity_and_openapi(tmp_path):
    assert sha256(verified_source_pdf(SOURCE_SHA256).read_bytes()).hexdigest() == SOURCE_SHA256
    settings = Settings(storage_root=tmp_path, database_url="postgresql+psycopg://user:pass@localhost/test")
    with TestClient(create_app(settings)) as client:
        schema = client.get("/openapi.json").json()
        assert "/api/v1/rule-sources/{source_hash}/file" in schema["paths"]
        assert "RuleSourceReference" in schema["components"]["schemas"]
        response = client.get(f"/api/v1/rule-sources/{SOURCE_SHA256}/file")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert sha256(response.content).hexdigest() == SOURCE_SHA256
        assert client.get("/api/v1/rule-sources/unknown/file").status_code == 404


def test_modified_source_is_not_served(tmp_path, monkeypatch):
    from backend.app.classification_engine import source_evidence
    altered = tmp_path / "altered.pdf"
    altered.write_bytes(b"%PDF altered")
    monkeypatch.setattr(source_evidence, "SOURCE_PDF", altered)
    with pytest.raises(ValueError):
        verified_source_pdf(SOURCE_SHA256)


@pytest.mark.parametrize("upper,lower,expected", [("60", None, None), (None, "60", None), ("0", None, False), ("60", "0", False), ("60", "60", True)])
def test_unreported_coating_face_is_not_false(upper, lower, expected):
    class EmptyRows:
        def all(self):
            return []
    class Session:
        def scalars(self, statement):
            return EmptyRows()
    item = SimpleNamespace(id=1, heat_id=1, form="flat_rolled", coiled=True,
                           rolling="cold", width_mm=Decimal("1220"), thickness_mm=Decimal("1"),
                           properties_json={"coating": {"metal": "Zn", "superior_g_m2": upper, "inferior_g_m2": lower}})
    assert ClassificationService._facts(Session(), item).coating_both_sides is expected


def test_manual_stainless_series_requires_explicit_valid_value():
    assert "stainless_series" in ReviewService.allowed_manual_fields
    ReviewService._validate_normalized("stainless_series", "300")
    ReviewService._validate_normalized("stainless_series", None)
    with pytest.raises(ApplicationError):
        ReviewService._validate_normalized("stainless_series", "304")
