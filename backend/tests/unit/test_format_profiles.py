from __future__ import annotations

import json
from pathlib import Path
import pytest

from backend.app.certificate_parser.format_profiles import (
    KNOWN_PROFILES,
    evaluate_format_profiles,
)
from backend.app.domain.document import DocumentLayout, PageLayout, PageSource, TextBlock
from backend.app.domain.document import BoundingBox

SAMPLES_DIR = Path(__file__).parents[3] / "data" / "samples"


def _doc_with_text(name: str, text: str) -> DocumentLayout:
    blocks = (TextBlock(1, text, BoundingBox(0, 0, 100, 100), source=PageSource.DIGITAL),)
    page = PageLayout(1, 612, 792, 0, PageSource.DIGITAL, blocks=blocks)
    return DocumentLayout(name, "hash123", (page,))


def test_known_molino_1_matches_profile_above_threshold():
    text = (
        "BX STEEL POSCO COLD ROLLED SHEET CO., LTD. "
        "MILL TEST CERTIFICATE E02511200001 "
        "BTA BLZ112-24-ASTM A1008 DDS-m-FB-PT.T-PW.T "
        "Cold-rolled steel strip PACK NO 25BH2B7550200"
    )
    doc = _doc_with_text("m1.pdf", text)
    name, score, signals = evaluate_format_profiles(doc)
    assert name == "MOLINO_1_BX_POSCO"
    assert score >= 0.85
    assert any("required:bx steel posco" in s for s in signals)


def test_known_molino_2_matches_profile():
    text = (
        "BENGANG STEEL PLATES COLD ROLLED SHEET CO., LTD. "
        "INSPECTION CERTIFICATE E02604270139 "
        "SAE1010MOD-m-FB-PT.T-PW.T BTA BLZ043-23 "
        "Cold-rolled steel strip"
    )
    doc = _doc_with_text("m2.pdf", text)
    name, score, signals = evaluate_format_profiles(doc)
    assert name == "MOLINO_2_BENGANG"
    assert score >= 0.85


def test_known_molino_3_matches_profile():
    text = (
        "CHINA STEEL CORPORATION CERTIFICATE OF QUALITY "
        "CERTIFICATE NO: 150612H0039 HANWA CO., LTD. "
        "SAE 1035 MILL EDGE SHEET COIL"
    )
    doc = _doc_with_text("m3.pdf", text)
    name, score, signals = evaluate_format_profiles(doc)
    assert name == "MOLINO_3_CHINA_STEEL"
    assert score >= 0.85


def test_known_molino_4_matches_profile():
    text = (
        "POSCO QUALITY CERTIFICATE ORDER NO: 240816-FZ01PS "
        "EG COIL (ZN) SECC CR-FREE PHOSPHATE LADLE ANALYSIS"
    )
    doc = _doc_with_text("m4.pdf", text)
    name, score, signals = evaluate_format_profiles(doc)
    assert name == "MOLINO_4_POSCO_EG"
    assert score >= 0.85


def test_negative_signals_reject_impostor_format():
    # Document contains "POSCO" and "SECC" but also "BENGANG", so it's not Molino 4
    text = "POSCO SECC EG COIL BENGANG STEEL PLATES"
    doc = _doc_with_text("impostor.pdf", text)
    name, score, _ = evaluate_format_profiles(doc)
    assert name != "MOLINO_4_POSCO_EG"


def test_unknown_layout_does_not_match_any_known_profile():
    text = (
        "ALTOS HORNOS DE MEXICO S.A.B. DE C.V. "
        "CERTIFICADO DE CALIDAD No. 98124 "
        "NORMA ASTM A36 LAMINADO EN CALIENTE "
        "COLADA 45912 ESPESOR 6.35 ANCHO 1500"
    )
    doc = _doc_with_text("unknown.pdf", text)
    name, score, _ = evaluate_format_profiles(doc)
    assert name is None
    assert score < 0.85
