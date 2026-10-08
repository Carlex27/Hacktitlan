from __future__ import annotations

from decimal import Decimal
import pytest

from backend.app.classification_engine import (
    BranchStatus,
    CandidateFactor,
    Chapter72ClassificationEngine,
    Chapter72CoverageMatrix,
    ClassificationCandidate,
    ClassificationOutcome,
    DiscardedCandidate,
    ProductFacts,
    RuleSetImmutabilityError,
    StepOutcome,
    compare_rule_sets,
    get_coverage_matrix,
    validate_rule_set_immutability,
)
from backend.app.domain.enums import RuleSetStatus


def non_alloy_chemistry(**overrides: str) -> dict[str, Decimal]:
    values = {
        "C": "0.08", "Al_total": "0.02", "B": "0", "Cr": "0.01",
        "Co": "0", "Cu": "0.01", "Pb": "0", "Mn": "0.34",
        "Mo": "0", "Ni": "0.01", "Nb": "0", "Si": "0.02",
        "Ti": "0", "W": "0", "V": "0", "Zr": "0",
        "OtherIndividual": "0",
    }
    values.update(overrides)
    return {key: Decimal(value) for key, value in values.items()}


def stainless_chemistry(**overrides: str) -> dict[str, Decimal]:
    values = {
        "C": "0.04", "Al_total": "0.01", "B": "0", "Cr": "18.2",
        "Co": "0", "Cu": "0.2", "Pb": "0", "Mn": "1.2",
        "Mo": "0.1", "Ni": "8.1", "Nb": "0", "Si": "0.4",
        "Ti": "0", "W": "0", "V": "0", "Zr": "0",
        "OtherIndividual": "0",
    }
    values.update(overrides)
    return {key: Decimal(value) for key, value in values.items()}


def make_facts(**overrides) -> ProductFacts:
    default_values = {
        "product_id": "test-item-1",
        "form": "flat_rolled",
        "coiled": True,
        "rolling": "cold",
        "width_mm": Decimal("1000"),
        "thickness_mm": Decimal("1.5"),
        "composition_pct": non_alloy_chemistry(),
        "coated": False,
        "yield_strength_mpa": Decimal("250"),
    }
    default_values.update(overrides)
    return ProductFacts(**default_values)


# ---------------------------------------------------------------------------
# 1. Coverage Matrix Complete Mapping Tests
# ---------------------------------------------------------------------------


def test_coverage_matrix_complete_mapping():
    matrix = get_coverage_matrix()
    summary = matrix.summary()

    # Total catalog entries in Chapter 72
    assert summary["total_catalog_entries"] == 614
    assert summary["by_kind"] == {"heading": 29, "fraction": 176, "nico": 409}

    # Verify status breakdown
    status_counts = summary["overall_by_status"]
    assert status_counts[BranchStatus.IMPLEMENTED.value] == 285
    assert status_counts[BranchStatus.BLOCKED_BY_MISSING_FACT.value] == 17
    assert status_counts[BranchStatus.AMBIGUOUS_SOURCE.value] == 2
    assert status_counts[BranchStatus.NOT_IMPLEMENTED.value] == 6
    assert status_counts[BranchStatus.OUT_OF_SCOPE.value] == 304

    # All 9 flat-rolled headings are in scope
    flat_headings = {
        "7208", "7209", "7210", "7211", "7212", "7219", "7220", "7225", "7226"
    }
    assert set(summary["flat_rolled_headings"]) == flat_headings

    # Zero unmapped entries
    total_accounted = sum(status_counts.values())
    assert total_accounted == 614


def test_coverage_matrix_all_entries_have_valid_status_and_facts():
    matrix = get_coverage_matrix()
    for entry in matrix.entries:
        assert entry.status in BranchStatus
        if entry.status == BranchStatus.IMPLEMENTED:
            assert len(entry.required_facts) > 0
            assert entry.notes is not None
        elif entry.status == BranchStatus.BLOCKED_BY_MISSING_FACT:
            assert len(entry.required_facts) > 0
            assert "Requiere hechos externos" in (entry.notes or "")
        elif entry.status == BranchStatus.AMBIGUOUS_SOURCE:
            assert entry.compact_code == "72193502"
        elif entry.status == BranchStatus.NOT_IMPLEMENTED:
            assert entry.required_facts == ("implemented_tariff_branch",)


def test_coverage_reports_unreachable_catalog_fractions():
    matrix = get_coverage_matrix()
    assert get_coverage_matrix() is not matrix
    for code in ("72089099", "72099099", "72104199"):
        assert matrix.get(code).status is BranchStatus.NOT_IMPLEMENTED


# ---------------------------------------------------------------------------
# 2. Boundary and Threshold Tests (Below, At, Above)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "cr_val,c_val,expected_outcome_type",
    [
        ("10.4999", "0.04", "non_alloy_or_alloy"),
        ("10.5000", "0.04", "stainless"),
        ("10.5001", "0.04", "stainless"),
        ("10.5000", "1.2000", "stainless"),
        ("10.5000", "1.2001", "other_alloy"),  # Exceeds 1.2% C -> Not stainless, but alloy because Cr >= 0.3%
    ],
)
def test_stainless_cr_and_carbon_thresholds(cr_val, c_val, expected_outcome_type):
    engine = Chapter72ClassificationEngine()
    chemistry = non_alloy_chemistry(Cr=cr_val, C=c_val)
    facts = make_facts(
        width_mm=Decimal("1000"),
        thickness_mm=Decimal("2.0"),
        composition_pct=chemistry,
        rolling="cold",
    )
    result = engine.classify(facts)
    if expected_outcome_type == "stainless":
        assert result.product_type == "flat_rolled_stainless"
        assert result.fraction is not None and result.fraction.startswith("7219")
    elif expected_outcome_type == "other_alloy":
        assert result.product_type == "flat_rolled_other_alloy"
        assert result.fraction is not None and result.fraction.startswith("7225")
    else:
        # 10.4999% Cr is below stainless threshold 10.5% but above alloy Cr threshold 0.3%
        assert result.product_type == "flat_rolled_other_alloy"


@pytest.mark.parametrize(
    ("boron", "expected_type"),
    [
        ("0.00079", "flat_rolled_non_alloy"),
        ("0.00080", "flat_rolled_other_alloy"),
        ("0.00081", "flat_rolled_other_alloy"),
    ],
)
def test_boron_threshold_is_inclusive(boron, expected_type):
    result = Chapter72ClassificationEngine().classify(
        make_facts(composition_pct=non_alloy_chemistry(B=boron))
    )
    assert result.product_type == expected_type


@pytest.mark.parametrize(
    "width_mm,expected_heading",
    [
        (Decimal("599.9"), "7211"),
        (Decimal("600.0"), "7209"),
        (Decimal("600.1"), "7209"),
    ],
)
def test_width_boundary_600mm(width_mm, expected_heading):
    engine = Chapter72ClassificationEngine()
    facts = make_facts(
        width_mm=width_mm,
        thickness_mm=Decimal("1.5"),
        rolling="cold",
        coated=False,
    )
    result = engine.classify(facts)
    assert result.fraction is not None
    assert result.fraction.startswith(expected_heading)


@pytest.mark.parametrize(
    "yield_mpa,expected_nico",
    [
        (Decimal("354.9"), "99"),
        (Decimal("355.0"), "01"),
        (Decimal("355.1"), "01"),
    ],
)
def test_yield_strength_boundary_355_mpa(yield_mpa, expected_nico):
    engine = Chapter72ClassificationEngine()
    facts = make_facts(
        width_mm=Decimal("1000"),
        thickness_mm=Decimal("1.5"),
        yield_strength_mpa=yield_mpa,
        rolling="cold",
    )
    result = engine.classify(facts)
    assert result.fraction == "72091601"
    assert result.nico == expected_nico


@pytest.mark.parametrize(
    "thickness_mm,expected_fraction",
    [
        (Decimal("0.499"), "72091801"),
        (Decimal("0.500"), "72091701"),
        (Decimal("0.501"), "72091701"),
        (Decimal("0.999"), "72091701"),
        (Decimal("1.000"), "72091701"),
        (Decimal("1.001"), "72091601"),
        (Decimal("2.999"), "72091601"),
        (Decimal("3.000"), "72091504"),
        (Decimal("3.001"), "72091504"),
    ],
)
def test_cold_rolled_thickness_boundaries(thickness_mm, expected_fraction):
    engine = Chapter72ClassificationEngine()
    facts = make_facts(
        width_mm=Decimal("1000"),
        thickness_mm=thickness_mm,
        rolling="cold",
    )
    result = engine.classify(facts)
    assert result.fraction == expected_fraction


@pytest.mark.parametrize(
    ("thickness", "expected_nico"),
    [("0.349", "01"), ("0.350", "01"), ("0.351", "02")],
)
def test_galvanized_035mm_boundary(thickness, expected_nico):
    result = Chapter72ClassificationEngine().classify(make_facts(
        coated=True, coating_metal="zinc", thickness_mm=Decimal(thickness)
    ))
    assert (result.fraction, result.nico) == ("72104999", expected_nico)


@pytest.mark.parametrize(
    ("thickness", "expected_fraction"),
    [("4.749", "72111999"), ("4.750", "72111491"), ("4.751", "72111491")],
)
def test_narrow_hot_475mm_boundary(thickness, expected_fraction):
    result = Chapter72ClassificationEngine().classify(make_facts(
        width_mm=Decimal("400"), rolling="hot", thickness_mm=Decimal(thickness)
    ))
    assert result.fraction == expected_fraction


@pytest.mark.parametrize(
    ("thickness", "expected_fraction"),
    [("9.999", "72191202"), ("10.000", "72191202"), ("10.001", "72191101")],
)
def test_stainless_hot_10mm_boundary(thickness, expected_fraction):
    result = Chapter72ClassificationEngine().classify(make_facts(
        rolling="hot", thickness_mm=Decimal(thickness),
        composition_pct=stainless_chemistry(),
    ))
    assert result.fraction == expected_fraction


# ---------------------------------------------------------------------------
# 3. Heading-by-Heading Flat-Rolled Deterministic Routing Tests
# ---------------------------------------------------------------------------


def test_heading_7210_coated_wide():
    engine = Chapter72ClassificationEngine()

    # Tinplate >= 0.5mm -> 7210.11.01
    f_tin_thick = make_facts(coated=True, coating_metal="tin", thickness_mm=Decimal("0.6"))
    res_tin_thick = engine.classify(f_tin_thick)
    assert res_tin_thick.fraction == "72101101"
    assert res_tin_thick.nico == "00"

    # Tinplate < 0.5mm -> 7210.12.04
    f_tin_thin = make_facts(coated=True, coating_metal="tin", thickness_mm=Decimal("0.3"))
    res_tin_thin = engine.classify(f_tin_thin)
    assert res_tin_thin.fraction == "72101204"

    # Hot-dip galvanized relief -> 7210.41.01
    f_galv_relief = make_facts(coated=True, coating_metal="zinc", pattern_in_relief=True)
    res_galv_relief = engine.classify(f_galv_relief)
    assert res_galv_relief.fraction == "72104101"

    # Hot-dip galvanized <= 0.35mm -> 7210.49.99 NICO 01
    f_galv_thin = make_facts(coated=True, coating_metal="zinc", thickness_mm=Decimal("0.30"))
    res_galv_thin = engine.classify(f_galv_thin)
    assert res_galv_thin.fraction == "72104999"
    assert res_galv_thin.nico == "01"

    # Aluminum-zinc alloy -> 7210.61.01
    f_alzn = make_facts(coated=True, coating_metal="al-zn")
    res_alzn = engine.classify(f_alzn)
    assert res_alzn.fraction == "72106101"

    # Painted / plastic -> 7210.70.02
    f_paint = make_facts(coated=True, coating_metal="paint")
    res_paint = engine.classify(f_paint)
    assert res_paint.fraction == "72107002"


def test_heading_7211_narrow_non_alloy():
    engine = Chapter72ClassificationEngine()

    # Hot rolled narrow >= 4.75mm -> 7211.14.91
    f_hot_thick = make_facts(width_mm=Decimal("400"), rolling="hot", thickness_mm=Decimal("5.0"), coiled=True)
    res_hot_thick = engine.classify(f_hot_thick)
    assert res_hot_thick.fraction == "72111491"

    # Hot rolled narrow < 4.75mm -> 7211.19.99
    f_hot_thin = make_facts(width_mm=Decimal("400"), rolling="hot", thickness_mm=Decimal("3.0"), coiled=True)
    res_hot_thin = engine.classify(f_hot_thin)
    assert res_hot_thin.fraction == "72111999"

    # Cold rolled narrow C >= 0.25% -> 7211.29.99
    chem_med_c = non_alloy_chemistry(C="0.30")
    f_cold_med_c = make_facts(width_mm=Decimal("400"), rolling="cold", composition_pct=chem_med_c)
    res_cold_med_c = engine.classify(f_cold_med_c)
    assert res_cold_med_c.fraction == "72112999"
    assert res_cold_med_c.nico == "01"

    # Cold rolled narrow C < 0.25% <= 0.35mm -> 7211.23.03 NICO 01
    f_cold_low_c = make_facts(width_mm=Decimal("400"), rolling="cold", thickness_mm=Decimal("0.30"))
    res_cold_low_c = engine.classify(f_cold_low_c)
    assert res_cold_low_c.fraction == "72112303"
    assert res_cold_low_c.nico == "01"


def test_heading_7212_narrow_coated():
    engine = Chapter72ClassificationEngine()

    # Narrow clad -> 7212.60.04
    f_clad = make_facts(width_mm=Decimal("400"), coated=True, clad=True)
    res_clad = engine.classify(f_clad)
    assert res_clad.fraction == "72126004"

    # Narrow electrolytic zinc -> 7212.20.03
    f_ez = make_facts(width_mm=Decimal("400"), coated=True, coating_metal="zinc", coating_process="electrolytic", coating_both_sides=True)
    res_ez = engine.classify(f_ez)
    assert res_ez.fraction == "72122003"
    assert res_ez.nico == "01"

    # Narrow painted -> 7212.40.04
    f_paint = make_facts(width_mm=Decimal("400"), coated=True, coating_metal="paint")
    res_paint = engine.classify(f_paint)
    assert res_paint.fraction == "72124004"


def test_heading_7219_stainless_wide():
    engine = Chapter72ClassificationEngine()

    # Hot rolled coiled > 10mm -> 7219.11.01
    f_hot_10 = make_facts(
        width_mm=Decimal("1200"),
        rolling="hot",
        coiled=True,
        thickness_mm=Decimal("12.0"),
        composition_pct=stainless_chemistry(),
    )
    res_hot_10 = engine.classify(f_hot_10)
    assert res_hot_10.fraction == "72191101"
    assert res_hot_10.nico == "00"  # 7219.11.01 has only NICO 00

    # Hot rolled coiled 3.5mm -> 7219.13.01 with NICO 01 (300 series)
    f_hot_3 = make_facts(
        width_mm=Decimal("1200"),
        rolling="hot",
        coiled=True,
        thickness_mm=Decimal("3.5"),
        composition_pct=stainless_chemistry(),
    )
    res_hot_3 = engine.classify(f_hot_3)
    assert res_hot_3.fraction == "72191301"
    assert res_hot_3.nico == "01"

    # Cold rolled >= 4.75mm -> 7219.31.01
    f_cold_thick = make_facts(
        width_mm=Decimal("1200"),
        rolling="cold",
        thickness_mm=Decimal("5.0"),
        composition_pct=stainless_chemistry(),
    )
    res_cold_thick = engine.classify(f_cold_thick)
    assert res_cold_thick.fraction == "72193101"
    assert res_cold_thick.nico == "01"


def test_heading_7220_stainless_narrow():
    engine = Chapter72ClassificationEngine()

    # Hot rolled narrow >= 4.75mm -> 7220.11.01
    f_hot_thick = make_facts(
        width_mm=Decimal("400"),
        rolling="hot",
        thickness_mm=Decimal("5.0"),
        composition_pct=stainless_chemistry(),
    )
    res_hot_thick = engine.classify(f_hot_thick)
    assert res_hot_thick.fraction == "72201101"

    # Cold rolled narrow -> 7220.20.03
    f_cold = make_facts(
        width_mm=Decimal("400"),
        rolling="cold",
        thickness_mm=Decimal("1.5"),
        composition_pct=stainless_chemistry(),
    )
    res_cold = engine.classify(f_cold)
    assert res_cold.fraction == "72202003"


def test_heading_7225_other_alloy_wide():
    engine = Chapter72ClassificationEngine()
    alloy_chem = non_alloy_chemistry(Ti="0.06")

    # Silicon electrical grain-oriented -> 7225.11.01
    f_grain = make_facts(
        width_mm=Decimal("1000"),
        grain_oriented=True,
        composition_pct=alloy_chem,
    )
    res_grain = engine.classify(f_grain)
    assert res_grain.fraction == "72251101"

    # Hot coiled other alloy -> 7225.30.91
    f_hot_coiled = make_facts(
        width_mm=Decimal("1000"),
        rolling="hot",
        coiled=True,
        composition_pct=alloy_chem,
    )
    res_hot_coiled = engine.classify(f_hot_coiled)
    assert res_hot_coiled.fraction == "72253091"

    # Coated other alloy galvanized -> 7225.92.01
    f_coated = make_facts(
        width_mm=Decimal("1000"),
        coated=True,
        coating_metal="zinc",
        composition_pct=alloy_chem,
    )
    res_coated = engine.classify(f_coated)
    assert res_coated.fraction == "72259201"


def test_heading_7226_other_alloy_narrow():
    engine = Chapter72ClassificationEngine()
    alloy_chem = non_alloy_chemistry(Ti="0.06")

    # Narrow grain oriented -> 7226.11.01
    f_grain = make_facts(
        width_mm=Decimal("400"),
        grain_oriented=True,
        composition_pct=alloy_chem,
    )
    res_grain = engine.classify(f_grain)
    assert res_grain.fraction == "72261101"

    # Narrow high speed steel -> 7226.20.01
    f_hss = make_facts(
        width_mm=Decimal("400"),
        high_speed_steel=True,
        composition_pct=alloy_chem,
    )
    res_hss = engine.classify(f_hss)
    assert res_hss.fraction == "72262001"

    # Narrow hot rolled -> 7226.91.07
    f_hot = make_facts(
        width_mm=Decimal("400"),
        rolling="hot",
        composition_pct=alloy_chem,
    )
    res_hot = engine.classify(f_hot)
    assert res_hot.fraction == "72269107"


# ---------------------------------------------------------------------------
# 4. Source Anomaly & Ambiguity Handling (7219.35.02)
# ---------------------------------------------------------------------------


def test_ambiguous_source_code_7219_35_02_generates_ambiguous_outcome():
    engine = Chapter72ClassificationEngine()
    # Cold rolled stainless wide with thickness <= 1.0 mm encounters the duplicated catalog code 7219.35.02
    facts = make_facts(
        width_mm=Decimal("1000"),
        thickness_mm=Decimal("0.8"),
        rolling="cold",
        composition_pct=stainless_chemistry(),
    )
    result = engine.classify(facts)
    assert result.outcome is ClassificationOutcome.NEEDS_REVIEW
    assert "ambiguous_source_code_7219_35_02" in result.missing_fields
    ambiguous_step = next(
        step for step in result.steps
        if step.rule_code == "chapter72.stainless.source_anomaly_7219_35_02"
    )
    assert ambiguous_step.outcome is StepOutcome.AMBIGUOUS
    assert "7219.35.02" in ambiguous_step.explanation


def test_external_facts_are_reported_by_executable_branches():
    engine = Chapter72ClassificationEngine()
    magnetic = engine.classify(make_facts(
        composition_pct=non_alloy_chemistry(Ti="0.06"), grain_oriented=True
    ))
    tinplate = engine.classify(make_facts(
        coated=True, coating_metal="tin", thickness_mm=Decimal("0.3")
    ))
    clad = engine.classify(make_facts(width_mm=Decimal("400"), coated=True, clad=True))

    assert {"magnetic_loss_w_per_kg", "magnetic_induction_tesla"} <= set(magnetic.missing_fields)
    assert {"secondary_reduction_ratio", "can_body_end_use"} <= set(tinplate.missing_fields)
    assert "cladding_weight_percentage" in clad.missing_fields


# ---------------------------------------------------------------------------
# 5. Missing Facts Never Converted to Zero or False
# ---------------------------------------------------------------------------


def test_missing_facts_remain_null_and_conditional():
    engine = Chapter72ClassificationEngine()
    # Coiled is None
    facts = make_facts(
        width_mm=Decimal("1000"),
        thickness_mm=Decimal("2.0"),
        rolling="hot",
        coiled=None,
    )
    result = engine.classify(facts)
    assert result.outcome is ClassificationOutcome.NEEDS_REVIEW
    assert "coiled" in result.missing_fields
    assert result.fraction is None


# ---------------------------------------------------------------------------
# 6. Candidate Validation & Discard Reasons
# ---------------------------------------------------------------------------


def test_candidates_all_exist_in_catalog():
    engine = Chapter72ClassificationEngine()
    facts = make_facts(thickness_mm=Decimal("1.5"))
    result = engine.classify(facts)
    for candidate in result.ranked_candidates:
        # validate_result raises ValueError if candidate is invalid/not in catalog
        engine.catalog.validate_result(candidate.fraction, candidate.nico)
        assert engine.catalog.description(candidate.fraction, candidate.nico) is not None


# ---------------------------------------------------------------------------
# 7. Versioning, Immutability & Retired Rule Set Rejection
# ---------------------------------------------------------------------------


def test_rule_set_immutability_enforcement():
    # Draft allows changes without error
    validate_rule_set_immutability("draft", "manifest_json")

    # Approved raises error
    with pytest.raises(RuleSetImmutabilityError, match="Cannot modify 'manifest_json' on a rule set with status 'approved'"):
        validate_rule_set_immutability("approved", "manifest_json")

    # Retired raises error
    with pytest.raises(RuleSetImmutabilityError, match="Cannot modify 'manifest_json' on a rule set with status 'retired'"):
        validate_rule_set_immutability("retired", "manifest_json")


def test_compare_rule_sets_auditing():
    current_manifest = {
        "version": "1.0.0",
        "catalog_sha256": "abc123",
        "source_hash": "src1",
        "rules": {"r1": "v1", "r2": "v1"},
    }
    target_manifest = {
        "version": "1.1.0",
        "catalog_sha256": "abc123",
        "source_hash": "src2",
        "rules": {"r1": "v1", "r2": "v2", "r3": "v1"},
    }
    diff = compare_rule_sets(current_manifest, target_manifest)
    assert diff["current_version"] == "1.0.0"
    assert diff["target_version"] == "1.1.0"
    assert diff["catalog_changed"] is False
    assert diff["source_changed"] is True
    assert diff["added_rules"] == ["r3"]
    assert diff["removed_rules"] == []
    assert diff["modified_rules"] == ["r2"]
    assert diff["has_breaking_changes"] is True


def test_retired_rule_set_rejected_for_new_classification():
    from unittest.mock import MagicMock
    from backend.app.application.classification_service import ClassificationService
    from backend.app.domain.errors import ApplicationError

    session = MagicMock()
    retired_rule_set = MagicMock()
    retired_rule_set.status = RuleSetStatus.RETIRED.value
    session.get.return_value = retired_rule_set

    with pytest.raises(ApplicationError) as exc_info:
        ClassificationService._rule_set(session, rule_set_id=99)
    assert exc_info.value.code == "rule_set_retired"
    assert "retirado" in exc_info.value.message


def test_historical_snapshot_reclassification_reproducibility():
    from backend.app.application.classification_service import ClassificationService

    # 1. Original facts
    engine = Chapter72ClassificationEngine()
    original_facts = make_facts(
        width_mm=Decimal("1200"),
        thickness_mm=Decimal("1.8"),
        yield_strength_mpa=Decimal("380"),
        rolling="cold",
    )
    original_decision = engine.classify(original_facts)

    # 2. Generate historical snapshot
    snapshot = ClassificationService._snapshot(original_facts)

    # 3. Reconstruct facts from historical snapshot (as done when reviewing past classifications)
    reconstructed_facts = ClassificationService._facts_from_snapshot(snapshot)

    # 4. Reclassify using the same engine
    reclassified_decision = engine.classify(reconstructed_facts)

    # 5. Verify perfect deterministic reproducibility
    assert reclassified_decision.outcome == original_decision.outcome
    assert reclassified_decision.product_type == original_decision.product_type
    assert reclassified_decision.fraction == original_decision.fraction
    assert reclassified_decision.nico == original_decision.nico
    assert reclassified_decision.missing_fields == original_decision.missing_fields
    assert len(reclassified_decision.ranked_candidates) == len(original_decision.ranked_candidates)
    assert len(reclassified_decision.steps) == len(original_decision.steps)
