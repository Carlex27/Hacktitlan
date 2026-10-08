from __future__ import annotations

import json
from pathlib import Path
import pytest

from backend.app.certificate_parser.mill_certificate import normalize_certificate

SAMPLES_DIR = Path(__file__).parents[3] / "data" / "samples"


def test_corpus_molino_1_exact_normalization():
    raw_path = SAMPLES_DIR / "molino-1.raw.json"
    raw = json.loads(raw_path.read_text(encoding="utf-8"))

    normalized = normalize_certificate(raw)
    products = normalized["products"]

    # 6 coils
    assert len(products) == 6
    assert normalized["validation"]["piece_count_matches"] is True
    assert normalized["validation"]["net_weight_matches"] is True
    assert normalized["validation"]["gross_weight_matches"] is True

    # Coils and heat
    expected_coils = [
        "25BH2B7550200",
        "25BH2B7560200",
        "25BH2B7570200",
        "25BH2B7580200",
        "25BH2B7590200",
        "25BH2B7600200",
    ]
    assert [p["product_id"] for p in products] == expected_coils
    assert all(p["heat_no"] == "2518114" for p in products)

    # Chemical composition scaling: 13 * 10^-4 = 0.0013%
    chem = products[0]["composition_pct"]
    assert chem["C"] == 0.0013
    assert chem["Si"] == 0.0
    assert chem["Mn"] == 0.12
    assert chem["P"] == 0.011
    assert chem["S"] == 0.008
    assert chem["Al_soluble"] == 0.031
    assert chem["Ti"] == 0.068

    # Dimensions and conditions
    p0 = products[0]
    assert p0["thickness_mm"] == 0.9
    assert p0["width_mm"] == 991.0
    assert p0["coiled"] is True
    assert p0["form"] == "flat_rolled"
    assert p0["rolling"] == "cold"
    assert p0["condition"] == ["annealed", "skin_passed"]
    assert p0["net_weight_kg"] == 7910.0
    assert p0["gross_weight_kg"] == 7970.0


def test_corpus_molino_2_rotation_and_missing_chemical_elements():
    raw_path = SAMPLES_DIR / "molino-2.raw.json"
    raw = json.loads(raw_path.read_text(encoding="utf-8"))

    normalized = normalize_certificate(raw)
    products = normalized["products"]

    # 1 coil
    assert len(products) == 1
    p = products[0]
    assert p["product_id"] == "263W220590210"
    assert p["heat_no"] == "2641568"
    assert p["thickness_mm"] == 1.71
    assert p["width_mm"] == 1220.0
    assert p["net_weight_kg"] == 8995.0
    assert p["gross_weight_kg"] == 9075.0

    # Chemistry: Si and Ti are NOT in certificate, so they must be absent (not zero!)
    chem = p["composition_pct"]
    assert chem["C"] == 0.08
    assert chem["Mn"] == 0.34
    assert chem["P"] == 0.015
    assert chem["S"] == 0.008
    assert chem["Al_total"] == 0.029
    assert "Si" not in chem
    assert "Ti" not in chem

    # Mechanical properties
    props = p["mechanical_properties"]
    assert props["yield_strength_mpa"] == 230.0
    assert props["tensile_strength_mpa"] == 363.0
    assert props["elongation_pct"] == 46.5
    assert props["hardness_hrb"] == 51.3


def test_corpus_molino_3_ditto_marks_and_thickness_inheritance():
    raw_path = SAMPLES_DIR / "molino-3.raw.json"
    raw = json.loads(raw_path.read_text(encoding="utf-8"))

    normalized = normalize_certificate(raw)
    products = normalized["products"]

    # 11 coils, hot rolled, SAE 1035
    assert len(products) == 11
    assert normalized["validation"]["piece_count_matches"] is True
    assert normalized["validation"]["weight_matches"] is True

    # Check thickness and width inheritance on row 2 (which had ditto marks '"')
    p0 = products[0]
    p1 = products[1]
    assert p0["thickness_mm"] == 1.800
    assert p1["thickness_mm"] == 1.800
    assert p1["width_mm"] == 895.0
    assert p1["coiled"] is True
    assert p1["observations"]["thickness_mm"]["inherited"] is True

    # Heat 3VL99 chemistry
    assert p0["heat_no"] == "3VL99"
    chem_3vl99 = p0["composition_pct"]
    assert chem_3vl99["C"] == 0.35
    assert chem_3vl99["Mn"] == 0.63
    assert chem_3vl99["P"] == 0.017
    assert chem_3vl99["S"] == 0.001
    assert chem_3vl99["Si"] == 0.20
    assert chem_3vl99["Cu"] == 0.01
    assert chem_3vl99["Ni"] == 0.01
    assert chem_3vl99["Cr"] == 0.01
    assert chem_3vl99["Al_total"] == 0.019
    assert chem_3vl99["B"] == 0.0003
    assert chem_3vl99["Mo"] == 0.0
    assert chem_3vl99["N"] == 0.004

    # Row 1 chemistry inherited from row 0
    chem_p1 = p1["composition_pct"]
    assert chem_p1["C"] == 0.35
    assert p1["observations"]["composition_pct"]["C"]["inherited"] is True

    # Heat 1FN43 (row 2) chemistry
    p2 = products[2]
    assert p2["heat_no"] == "1FN43"
    chem_1fn43 = p2["composition_pct"]
    assert chem_1fn43["C"] == 0.33
    assert chem_1fn43["Mn"] == 0.64
    assert chem_1fn43["P"] == 0.016
    assert chem_1fn43["S"] == 0.002
    assert chem_1fn43["Si"] == 0.18
    assert chem_1fn43["Al_total"] == 0.025
    assert chem_1fn43["B"] == 0.0002


def test_corpus_molino_4_posco_subtotals_and_coating():
    raw_path = SAMPLES_DIR / "molino-4.raw.json"
    raw = json.loads(raw_path.read_text(encoding="utf-8"))

    normalized = normalize_certificate(raw)
    products = normalized["products"]

    # 6 coils
    assert len(products) == 6
    assert normalized["validation"]["piece_count_matches"] is True
    assert normalized["validation"]["weight_matches"] is True
    assert normalized["validation"]["subtotals_match"] is True

    # SECC electrolytic zinc
    p0 = products[0]
    assert p0["standard"] == "SECC"
    assert p0["thickness_mm"] == 1.21
    assert p0["width_mm"] == 914.0
    assert p0["coiled"] is True
    assert p0["coating"]["metal"] == "Zn"
    assert p0["coating"]["process"] == "electrolytic"
    assert p0["coating"]["superior_g_m2"] == 19.1
    assert p0["coating"]["inferior_g_m2"] == 19.1
    assert p0["coating"]["post_treatment"] == "PL (Cr-Free Phosphate)"

    # Ladle chemistry without decimal displacement
    chem0 = p0["composition_pct"]
    assert chem0["C"] == 0.0136
    assert chem0["Si"] == 0.020
    assert chem0["Mn"] == 0.116
    assert chem0["P"] == 0.0090
    assert chem0["S"] == 0.0061

    # Product 3 (heat SB05270)
    p3 = products[3]
    assert p3["thickness_mm"] == 1.52
    assert p3["width_mm"] == 914.0
    assert p3["coating"]["superior_g_m2"] == 19.5
    assert p3["coating"]["inferior_g_m2"] == 19.5
    chem3 = p3["composition_pct"]
    assert chem3["C"] == 0.0142
    assert chem3["Mn"] == 0.127
