"""Unit tests for document quality evaluation, product families, confidence, and anomalies."""

from decimal import Decimal
import pytest

from backend.app.domain.document_quality import (
    CONFIDENCE_THRESHOLD_MIN,
    DocumentQualityReport,
    ProductFamily,
    QualityCategory,
    QualityIssue,
    QualitySeverity,
    detect_product_family,
    validate_document_quality,
)


def test_detect_product_family():
    assert detect_product_family({"coiled": True, "form": "Coil"}) == ProductFamily.FLAT_ROLLED_COIL
    assert detect_product_family({"coiled": True, "form": ""}) == ProductFamily.FLAT_ROLLED_COIL
    assert detect_product_family({"coiled": False, "form": "Plate"}) == ProductFamily.FLAT_ROLLED_PLATE
    assert detect_product_family({"coiled": False, "form": "Placa"}) == ProductFamily.FLAT_ROLLED_PLATE
    assert detect_product_family({"coiled": None, "form": "rollo de acero"}) == ProductFamily.FLAT_ROLLED_COIL
    assert detect_product_family({"coiled": None, "form": "unknown"}) == ProductFamily.FLAT_ROLLED_GENERAL


def test_validate_document_quality_clean():
    metadata = {
        "certificate_no": "CERT-2026-001",
        "supplier": "Acero del Norte",
        "standard": "ASTM A36",
    }
    products = [
        {
            "id": 1,
            "product_identifier": "ROLL-01",
            "heat_id": 10,
            "coiled": True,
            "form": "coil",
            "thickness_mm": Decimal("3.50"),
            "width_mm": Decimal("1200.00"),
            "weight_kg": Decimal("15000.00"),
        }
    ]
    heats = [
        {"id": 10, "heat_no": "HEAT-8888", "standard": "ASTM A36", "grade": "Gr 36"}
    ]
    observations = [
        {
            "id": 101,
            "product_id": 1,
            "field_path": "thickness_mm",
            "confidence": 0.95,
            "unit": "mm",
            "source_text": "3.50 mm",
            "inherited": False,
        },
        {
            "id": 102,
            "product_id": 1,
            "field_path": "width_mm",
            "confidence": 0.92,
            "unit": "mm",
            "source_text": "1200 mm",
            "inherited": False,
        },
    ]
    compositions = [
        {
            "id": 201,
            "heat_id": 10,
            "element": "C",
            "percentage": Decimal("0.18"),
        },
        {
            "id": 202,
            "heat_id": 10,
            "element": "Mn",
            "percentage": Decimal("0.85"),
        },
    ]

    report = validate_document_quality(
        certificate_id=1,
        document_metadata=metadata,
        products=products,
        heats=heats,
        observations=observations,
        compositions=compositions,
    )

    assert report.status == "clean"
    assert report.blocking_count == 0
    assert report.warning_count == 0
    assert report.quality_score == 1.0
    assert report.product_family == ProductFamily.FLAT_ROLLED_COIL
    assert report.provenance_summary["digital_text"] == 2


def test_mandatory_fields_missing():
    metadata = {
        "certificate_no": None,  # Missing cert no -> blocking
        "supplier": None,        # Missing supplier -> warning
        "standard": None,        # Missing standard -> warning
    }
    products = [
        {
            "id": 1,
            "product_identifier": "ROLL-01",
            "heat_id": 10,
            "coiled": True,
            "thickness_mm": None,  # Missing thickness -> blocking
            "width_mm": None,      # Missing width -> blocking
        }
    ]
    heats = [{"id": 10, "heat_no": "H1"}]

    report = validate_document_quality(
        certificate_id=1,
        document_metadata=metadata,
        products=products,
        heats=heats,
        observations=[],
        compositions=[{"heat_id": 10, "element": "C", "percentage": Decimal("0.1")}],
    )

    assert report.status == "needs_review"
    assert report.blocking_count >= 3  # cert_no, thickness_mm, width_mm
    codes = {issue.code for issue in report.issues}
    assert "missing_certificate_number" in codes
    assert "missing_supplier" in codes
    assert "missing_standard" in codes
    assert "missing_required_field" in codes
    assert report.quality_score < 0.5


def test_impossible_dimensions():
    metadata = {"certificate_no": "C1"}
    products = [
        {
            "id": 1,
            "product_identifier": "ROLL-01",
            "heat_id": 10,
            "thickness_mm": Decimal("-2.5"),  # Impossible
            "width_mm": Decimal("0.0"),        # Impossible
            "weight_kg": Decimal("-100"),      # Impossible
        }
    ]
    heats = [{"id": 10, "heat_no": "H1"}]
    compositions = [{"heat_id": 10, "element": "C", "percentage": Decimal("0.2")}]

    report = validate_document_quality(
        certificate_id=1,
        document_metadata=metadata,
        products=products,
        heats=heats,
        observations=[],
        compositions=compositions,
    )

    impossible_issues = [i for i in report.issues if i.code == "impossible_dimension"]
    assert len(impossible_issues) == 3
    for iss in impossible_issues:
        assert iss.category == QualityCategory.CONTRADICTION
        assert iss.severity == QualitySeverity.BLOCKING


def test_chemistry_out_of_range_and_impossible_sum():
    metadata = {"certificate_no": "C1"}
    products = [
        {"id": 1, "product_identifier": "R1", "heat_id": 10, "thickness_mm": Decimal("3"), "width_mm": Decimal("1000")}
    ]
    heats = [{"id": 10, "heat_no": "H1"}]
    compositions = [
        {"heat_id": 10, "element": "Fe", "percentage": Decimal("95.0")},
        {"heat_id": 10, "element": "C", "percentage": Decimal("10.0")},  # Sum = 105.0% > 100%
        {"heat_id": 10, "element": "Si", "percentage": Decimal("110.0")}, # Out of range > 100%
    ]

    report = validate_document_quality(
        certificate_id=1,
        document_metadata=metadata,
        products=products,
        heats=heats,
        observations=[],
        compositions=compositions,
    )

    codes = [i.code for i in report.issues]
    assert "chemical_sum_exceeds_100" in codes
    assert "chemical_percentage_out_of_range" in codes


def test_duplicate_heat_conflict():
    metadata = {"certificate_no": "C1"}
    products = [
        {"id": 1, "product_identifier": "R1", "heat_id": 10, "thickness_mm": Decimal("3"), "width_mm": Decimal("1000")},
        {"id": 2, "product_identifier": "R2", "heat_id": 11, "thickness_mm": Decimal("3"), "width_mm": Decimal("1000")},
    ]
    heats = [
        {"id": 10, "heat_no": "H-999", "standard": "ASTM A36", "grade": "Gr 36"},
        {"id": 11, "heat_no": "H-999", "standard": "EN 10025", "grade": "S235JR"},  # Duplicate with conflicting standard
    ]
    compositions = [{"heat_id": 10, "element": "C", "percentage": Decimal("0.15")}]

    report = validate_document_quality(
        certificate_id=1,
        document_metadata=metadata,
        products=products,
        heats=heats,
        observations=[],
        compositions=compositions,
    )

    conflict_issues = [i for i in report.issues if i.code == "duplicate_heat_conflict"]
    assert len(conflict_issues) == 1
    assert conflict_issues[0].category == QualityCategory.CONTRADICTION
    assert conflict_issues[0].severity == QualitySeverity.BLOCKING


def test_orphaned_product():
    metadata = {"certificate_no": "C1"}
    products = [
        {"id": 1, "product_identifier": "R1", "heat_id": 999, "thickness_mm": Decimal("3"), "width_mm": Decimal("1000")}
    ]
    heats = [{"id": 10, "heat_no": "H1"}]  # heat_id 999 does not exist

    report = validate_document_quality(
        certificate_id=1,
        document_metadata=metadata,
        products=products,
        heats=heats,
        observations=[],
        compositions=[],
    )

    orphan_issues = [i for i in report.issues if i.code == "orphaned_product"]
    assert len(orphan_issues) == 1
    assert orphan_issues[0].category == QualityCategory.CONTRADICTION
    assert orphan_issues[0].severity == QualitySeverity.BLOCKING


def test_incoherent_units():
    metadata = {"certificate_no": "C1"}
    products = [
        {"id": 1, "product_identifier": "R1", "heat_id": 10, "thickness_mm": Decimal("3"), "width_mm": Decimal("1000")}
    ]
    heats = [{"id": 10, "heat_no": "H1"}]
    observations = [
        {
            "id": 1,
            "product_id": 1,
            "field_path": "thickness_mm",
            "unit": "inches",  # Incoherent unit (expected mm)
            "confidence": 0.95,
        },
        {
            "id": 2,
            "product_id": 1,
            "field_path": "composition_pct.C",
            "unit": "kg",      # Incoherent unit (expected %)
            "confidence": 0.95,
        },
    ]
    compositions = [{"heat_id": 10, "element": "C", "percentage": Decimal("0.15")}]

    report = validate_document_quality(
        certificate_id=1,
        document_metadata=metadata,
        products=products,
        heats=heats,
        observations=observations,
        compositions=compositions,
    )

    incoherent = [i for i in report.issues if i.code == "incoherent_unit"]
    assert len(incoherent) == 2
    assert all(i.category == QualityCategory.CONTRADICTION for i in incoherent)


def test_low_confidence_separation():
    metadata = {"certificate_no": "C1"}
    products = [
        {"id": 1, "product_identifier": "R1", "heat_id": 10, "thickness_mm": Decimal("3"), "width_mm": Decimal("1000")}
    ]
    heats = [{"id": 10, "heat_no": "H1"}]
    observations = [
        {
            "id": 1,
            "product_id": 1,
            "field_path": "thickness_mm",
            "unit": "mm",
            "confidence": 0.55,  # Below CONFIDENCE_THRESHOLD_MIN (0.70)
            "page_number": 1,
            "bbox": {"x": 10, "y": 20, "w": 30, "h": 40},
            "source_text": "ocr text",
        }
    ]
    compositions = [{"heat_id": 10, "element": "C", "percentage": Decimal("0.15")}]

    report = validate_document_quality(
        certificate_id=1,
        document_metadata=metadata,
        products=products,
        heats=heats,
        observations=observations,
        compositions=compositions,
    )

    low_conf = [i for i in report.issues if i.category == QualityCategory.LOW_CONFIDENCE]
    assert len(low_conf) == 1
    assert low_conf[0].field_path == "thickness_mm"
    assert low_conf[0].confidence == 0.55
    assert low_conf[0].severity == QualitySeverity.BLOCKING  # thickness is critical
    assert report.provenance_summary["ocr_text"] == 1


def test_invalid_length_and_weight_formats_are_blocking():
    report = validate_document_quality(
        certificate_id=1,
        document_metadata={"certificate_no": "C1"},
        products=[{
            "id": 1,
            "product_identifier": "P1",
            "heat_id": 10,
            "coiled": False,
            "thickness_mm": 3,
            "width_mm": 1000,
            "length_m": "ERROR",
            "weight_kg": "N/A",
        }],
        heats=[{"id": 10, "heat_no": "H1"}],
        observations=[],
        compositions=[{"heat_id": 10, "element": "C", "percentage": Decimal("0.15")}],
    )

    invalid_fields = {
        issue.field_path for issue in report.issues if issue.code == "invalid_dimension_format"
    }
    assert invalid_fields == {"length_m", "weight_kg"}
    assert report.status == "needs_review"
