from __future__ import annotations

from decimal import Decimal
import shutil

import pytest

from backend.app.classification_engine import (
    Chapter72ClassificationEngine,
    ClassificationOutcome,
    ProductFacts,
    StepOutcome,
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
    assert result.outcome is ClassificationOutcome.NEEDS_REVIEW
    assert result.fraction == "72091601"
    assert result.nico == "99"
    assert result.description == "Los demás."
    assert len(result.ranked_candidates) == 1
    assert "three_valid_candidates" in result.missing_fields


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
    assert result.outcome is ClassificationOutcome.NEEDS_REVIEW
    assert result.fraction == "72103002"
    assert result.nico == "01"


def test_contradictory_nicos_are_removed_instead_of_padding_to_three():
    result = Chapter72ClassificationEngine().classify(
        facts(thickness_mm=Decimal("3"), porcelain_exposed_parts=None)
    )

    assert result.outcome is ClassificationOutcome.NEEDS_REVIEW
    assert [(candidate.rank, candidate.fraction, candidate.nico) for candidate in result.ranked_candidates] == [
        (1, "72091504", "99"),
        (2, "72091504", "03"),
    ]
    assert all(candidate.support_level == "conditional" for candidate in result.ranked_candidates)
    discarded = {
        (candidate.fraction, candidate.nico): candidate.reason_code
        for candidate in result.discarded_candidates
    }
    assert discarded[("72091504", "01")] == "known_facts_conflict"
    assert discarded[("72091504", "02")] == "known_facts_conflict"


def test_candidate_list_never_pads_to_three():
    result = Chapter72ClassificationEngine().classify(facts())

    assert [(candidate.fraction, candidate.nico) for candidate in result.ranked_candidates] == [
        ("72091601", "99")
    ]


def test_other_alloy_fraction_can_be_known_while_nico_needs_review():
    chemistry = complete_non_alloy_chemistry(Ti="0.05")
    result = Chapter72ClassificationEngine().classify(facts(composition_pct=chemistry))
    assert result.outcome is ClassificationOutcome.NEEDS_REVIEW
    assert result.product_type == "flat_rolled_other_alloy"
    assert result.fraction == "72255091"
    assert result.nico is None
    assert "nico_qualifier" in result.missing_fields
    alloy_step = next(
        step for step in result.steps
        if step.rule_code == "chapter72.definition.other_alloy"
    )
    assert alloy_step.evidence_fields == ("composition_pct.Ti",)
    assert [(candidate.fraction, candidate.nico) for candidate in result.ranked_candidates] == [
        ("72255091", "99"),
        ("72255091", "08"),
        ("72255091", "09"),
    ]
    first = result.ranked_candidates[0]
    alloy_factor = next(
        factor for factor in first.factors
        if factor.rule_code == "chapter72.definition.other_alloy"
    )
    assert alloy_factor.observed == {"Ti": "0.05"}
    assert alloy_factor.expected == {"Ti": "0.05"}
    assert alloy_factor.evidence_fields == ("composition_pct.Ti",)
    assert first.factors[-1].rule_code == "chapter72.nico.72255091.99"


@pytest.mark.parametrize(
    ("titanium", "expected_product_type"),
    [
        ("0.049999", "flat_rolled_non_alloy"),
        ("0.05", "flat_rolled_other_alloy"),
        ("0.050001", "flat_rolled_other_alloy"),
    ],
)
def test_titanium_alloy_boundary_is_inclusive(titanium, expected_product_type):
    result = Chapter72ClassificationEngine().classify(
        facts(composition_pct=complete_non_alloy_chemistry(Ti=titanium))
    )

    assert result.product_type == expected_product_type
    if expected_product_type == "flat_rolled_other_alloy":
        assert any(
            factor.rule_code == "chapter72.definition.other_alloy"
            and factor.expected == {"Ti": "0.05"}
            and factor.observed == {"Ti": titanium}
            and factor.operator == ">="
            and factor.unit == "%"
            and factor.outcome == StepOutcome.MATCHED
            and factor.evidence_fields == ("composition_pct.Ti",)
            for candidate in result.ranked_candidates
            for factor in candidate.factors
        )
    else:
        assert not any(
            factor.rule_code == "chapter72.definition.other_alloy"
            for candidate in result.ranked_candidates
            for factor in candidate.factors
        )


def test_boron_alloy_candidate_respects_thickness_and_coiling():
    chemistry = complete_non_alloy_chemistry(B="0.0008")
    result = Chapter72ClassificationEngine().classify(facts(composition_pct=chemistry))

    assert [(candidate.fraction, candidate.nico) for candidate in result.ranked_candidates] == [
        ("72255091", "01"),
        ("72255091", "99"),
        ("72255091", "08"),
    ]


def test_hot_rolled_unknown_pattern_uses_only_thickness_compatible_fractions():
    result = Chapter72ClassificationEngine().classify(
        facts(
            rolling="hot",
            thickness_mm=Decimal("6"),
            pattern_in_relief=None,
            pickled=None,
        )
    )

    assert result.candidates == ("72081003", "72082502", "72083701")
    assert [(candidate.fraction, candidate.nico) for candidate in result.ranked_candidates] == [
        ("72081003", "02"),
        ("72082502", "99"),
        ("72083701", "02"),
    ]


def test_catalog_lists_nicos_for_a_fraction_in_source_order():
    entries = SourceProvidedCatalog().nicos_for_fraction("7225.50.91")

    assert [entry.raw["nico"] for entry in entries[:3]] == ["01", "02", "03"]


def test_non_flat_product_is_explicitly_out_of_scope():
    result = Chapter72ClassificationEngine().classify(facts(form="bar"))
    assert result.outcome is ClassificationOutcome.OUT_OF_SCOPE
    assert result.fraction is None


def test_same_snapshot_reproduces_exact_decision():
    engine = Chapter72ClassificationEngine()
    chemistry = complete_non_alloy_chemistry(B="0.0008")
    product = facts(composition_pct=chemistry)
    first = engine.classify(product)
    second = engine.classify(product)

    assert first == second
    assert len(first.ranked_candidates) == 3
    assert [c.rank for c in first.ranked_candidates] == [1, 2, 3]
    for c1, c2 in zip(first.ranked_candidates, second.ranked_candidates):
        assert c1.fraction == c2.fraction
        assert c1.nico == c2.nico
        assert [f.sequence for f in c1.factors] == [f.sequence for f in c2.factors]
        assert [f.rule_code for f in c1.factors] == [f.rule_code for f in c2.factors]
        assert [f.outcome for f in c1.factors] == [f.outcome for f in c2.factors]


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
