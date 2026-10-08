from __future__ import annotations

from decimal import Decimal
import shutil

import pytest

from backend.app.classification_engine import (
    Chapter72ClassificationEngine,
    ClassificationOutcome,
    ProductFacts,
)
from backend.app.classification_engine.catalog import DEFAULT_CATALOG_PATH, SourceProvidedCatalog


def complete_non_alloy_chemistry(**overrides: str) -> dict[str, Decimal]:
    values = {
        "C": "0.08", "Al_total": "0.02", "B": "0", "Cr": "0.01",
        "Co": "0", "Cu": "0.01", "Pb": "0", "Mn": "0.34",
        "Mo": "0", "Ni": "0.01", "Nb": "0", "Si": "0.02",
        "Ti": "0", "W": "0", "V": "0", "Zr": "0",
        "OtherIndividual": "0",
    }
    values.update(overrides)
    return {key: Decimal(value) for key, value in values.items()}


def facts(**changes) -> ProductFacts:
    values = {
        "product_id": "coil-1",
        "form": "flat_rolled",
        "coiled": True,
        "rolling": "cold",
        "width_mm": Decimal("1220"),
        "thickness_mm": Decimal("1.71"),
        "composition_pct": complete_non_alloy_chemistry(),
        "coated": False,
        "yield_strength_mpa": Decimal("230"),
    }
    values.update(changes)
    return ProductFacts(**values)


def test_missing_alloy_elements_never_become_zero():
    result = Chapter72ClassificationEngine().classify(
        facts(composition_pct={"C": Decimal("0.08"), "Mn": Decimal("0.34")})
    )
    assert result.outcome is ClassificationOutcome.NEEDS_REVIEW
    assert result.fraction is None
    assert "composition_pct.Cr" in result.missing_fields
    assert set(result.candidates) == {"7209", "7219", "7225"}


def test_cold_rolled_coil_between_one_and_three_mm():
    result = Chapter72ClassificationEngine().classify(facts())
    assert result.outcome is ClassificationOutcome.CLASSIFIED
    assert result.fraction == "72091601"
    assert result.nico == "99"
    assert result.description == "Los demás."


def test_high_strength_boundary_is_inclusive():
    result = Chapter72ClassificationEngine().classify(
        facts(yield_strength_mpa=Decimal("355"))
    )
    assert result.fraction == "72091601"
    assert result.nico == "01"


def test_one_mm_uses_720917_branch():
    result = Chapter72ClassificationEngine().classify(
        facts(thickness_mm=Decimal("1.0"))
    )
    assert result.fraction == "72091701"


def test_electrolytic_zinc_both_sides():
    result = Chapter72ClassificationEngine().classify(
        facts(
            coating_metal="Zn",
            coating_process="electrolytic",
            coating_both_sides=True,
            coated=True,
        )
    )
    assert result.outcome is ClassificationOutcome.CLASSIFIED
    assert result.fraction == "72103002"
    assert result.nico == "01"


def test_other_alloy_fraction_can_be_known_while_nico_needs_review():
    chemistry = complete_non_alloy_chemistry(Ti="0.05")
    result = Chapter72ClassificationEngine().classify(facts(composition_pct=chemistry))
    assert result.outcome is ClassificationOutcome.NEEDS_REVIEW
    assert result.product_type == "flat_rolled_other_alloy"
    assert result.fraction == "72255091"
    assert result.nico is None
    assert "nico_qualifier" in result.missing_fields


def test_non_flat_product_is_explicitly_out_of_scope():
    result = Chapter72ClassificationEngine().classify(facts(form="bar"))
    assert result.outcome is ClassificationOutcome.OUT_OF_SCOPE
    assert result.fraction is None


def test_same_snapshot_reproduces_exact_decision():
    engine = Chapter72ClassificationEngine()
    product = facts()
    assert engine.classify(product) == engine.classify(product)


def test_catalog_change_requires_new_rule_version(tmp_path):
    changed = tmp_path / "catalog.json"
    shutil.copy2(DEFAULT_CATALOG_PATH, changed)
    changed.write_text(changed.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="rule-version"):
        SourceProvidedCatalog(changed)


def test_duplicate_source_fraction_is_never_selected_silently():
    catalog = SourceProvidedCatalog()
    with pytest.raises(ValueError, match="ambiguous"):
        catalog.validate_result("72193502", None)


def test_carbon_above_steel_definition_needs_review():
    chemistry = complete_non_alloy_chemistry(C="2.01")
    result = Chapter72ClassificationEngine().classify(facts(composition_pct=chemistry))
    assert result.outcome is ClassificationOutcome.NEEDS_REVIEW
    assert "steel_definition_exception" in result.missing_fields


def test_missing_coating_state_is_not_treated_as_uncoated():
    result = Chapter72ClassificationEngine().classify(facts(coated=None))
    assert result.outcome is ClassificationOutcome.NEEDS_REVIEW
    assert result.fraction is None
    assert "coated" in result.missing_fields
    assert set(result.candidates) == {"7209", "7210"}
