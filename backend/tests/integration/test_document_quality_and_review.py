"""Integration tests for document quality report, review queue, gating, and reprocessing."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from backend.app.api.app import create_app
from backend.app.application.classification_service import ClassificationService
from backend.app.application.review_service import ReviewService
from backend.app.config import Settings
from backend.app.domain.enums import ApprovalStatus, ProcessingStatus
from backend.app.infrastructure.database.models import (
    ChemicalComposition,
    Correction,
    Document,
    Heat,
    Job,
    Manufacturer,
    MillCertificate,
    Observation,
    Product,
    RuleSet,
    StoredFile,
)


@pytest.fixture()
def review_settings(tmp_path: Path) -> Settings:
    base = Settings()
    database_url = base.test_database_url
    if not database_url:
        pytest.skip("Requires the explicit hacktitlan_test PostgreSQL database")
    assert database_url.rsplit("/", 1)[-1].split("?", 1)[0] == "hacktitlan_test"

    engine = create_engine(database_url)
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "TRUNCATE classification_selections, candidate_factors, classification_candidates, "
                    "evidence_links, decision_steps, classification_results, classification_runs, "
                    "corrections, observations, chemical_compositions, products, heats, "
                    "jobs, mill_certificates, documents, stored_files, manufacturers "
                    "RESTART IDENTITY CASCADE"
                )
            )
    finally:
        engine.dispose()

    return Settings(
        database_url=database_url,
        test_database_url=database_url,
        storage_root=tmp_path / "storage",
        backup_root=tmp_path / "backups",
    )


def create_sample_certificate(
    session: Session,
    *,
    thickness: Decimal | None = Decimal("2.50"),
    width: Decimal | None = Decimal("1250.00"),
    thickness_confidence: float = 0.95,
    approval_status: str = ApprovalStatus.NEEDS_REVIEW.value,
    doc_status: str = ProcessingStatus.NEEDS_REVIEW.value,
) -> tuple[Document, MillCertificate, Product, Heat]:
    token = uuid4().hex
    stored_file = StoredFile(
        sha256=token.ljust(64, "0"),
        original_name="quality-sample.pdf",
        storage_name=f"{token}.pdf",
        relative_path=f"test/{token}.pdf",
        media_type="application/pdf",
        size_bytes=1024,
    )
    session.add(stored_file)
    session.flush()

    document = Document(
        stored_file_id=stored_file.id,
        processing_status=doc_status,
        metadata_json={"title": "Certificado de Calidad", "pages": 1},
    )
    session.add(document)
    session.flush()

    mfr = Manufacturer(name=f"Aceros-{token[:6]}", normalized_name=f"aceros-{token[:6]}")
    session.add(mfr)
    session.flush()

    certificate = MillCertificate(
        document_id=document.id,
        manufacturer_id=mfr.id,
        certificate_no=f"MTR-{token[:8]}",
        standard="ASTM A36",
        product_name="Bobina Laminada en Caliente",
        approval_status=approval_status,
        demo_notice="DEMOSTRACIÓN",
    )
    session.add(certificate)
    session.flush()

    heat = Heat(
        certificate_id=certificate.id,
        heat_no=f"HEAT-{token[:6]}",
        standard="ASTM A36",
        grade="Gr 36",
    )
    session.add(heat)
    session.flush()

    product = Product(
        certificate_id=certificate.id,
        heat_id=heat.id,
        product_identifier=f"COIL-{token[:6]}",
        coiled=True,
        form="flat_rolled",
        rolling="hot",
        thickness_mm=thickness,
        width_mm=width,
        weight_kg=Decimal("12000.00"),
        properties_json={"coated": False},
    )
    session.add(product)
    session.flush()

    # Add chemistry to heat
    session.add(
        ChemicalComposition(
            heat_id=heat.id,
            element="C",
            percentage=Decimal("0.18"),
            raw_value_json="0.18",
            inherited=False,
        )
    )
    session.add(
        ChemicalComposition(
            heat_id=heat.id,
            element="Mn",
            percentage=Decimal("0.85"),
            raw_value_json="0.85",
            inherited=False,
        )
    )

    # Add observations
    obs_th = Observation(
        certificate_id=certificate.id,
        product_id=product.id,
        field_path="thickness_mm",
        raw_value_json=str(thickness) if thickness is not None else None,
        normalized_value_json=float(thickness) if thickness is not None else None,
        unit="mm",
        confidence=thickness_confidence,
        page_number=1,
        source_text=f"{thickness} mm",
        inherited=False,
        is_current=True,
    )
    obs_w = Observation(
        certificate_id=certificate.id,
        product_id=product.id,
        field_path="width_mm",
        raw_value_json=str(width) if width is not None else None,
        normalized_value_json=float(width) if width is not None else None,
        unit="mm",
        confidence=0.92,
        page_number=1,
        source_text=f"{width} mm",
        inherited=False,
        is_current=True,
    )
    session.add_all([obs_th, obs_w])
    session.flush()

    return document, certificate, product, heat


def test_quality_report_endpoint_clean_and_not_found(review_settings: Settings):
    app = create_app(review_settings)
    client = TestClient(app)

    with app.state.sessions() as session:
        _, cert, _, _ = create_sample_certificate(session)
        session.commit()
        cert_id = cert.id

    # 1. Clean report
    res = client.get(f"/api/v1/certificates/{cert_id}/quality-report")
    assert res.status_code == 200
    body = res.json()
    assert body["error"] is None
    data = body["data"]
    assert data["certificate_id"] == cert_id
    assert data["status"] == "clean"
    assert data["quality_score"] == 1.0
    assert data["blocking_count"] == 0
    assert data["product_family"] == "flat_rolled_coil"
    assert "digital_text" in data["provenance_summary"]

    # 2. Not found
    res_404 = client.get("/api/v1/certificates/999999/quality-report")
    assert res_404.status_code == 404
    assert res_404.json()["error"]["code"] == "not_found"


def test_document_reviews_queue(review_settings: Settings):
    app = create_app(review_settings)
    client = TestClient(app)

    with app.state.sessions() as session:
        # Create one needing review and one clean draft
        _, cert_review, _, _ = create_sample_certificate(
            session,
            thickness=None,  # Missing thickness -> blocking issue
            approval_status=ApprovalStatus.NEEDS_REVIEW.value,
            doc_status=ProcessingStatus.NEEDS_REVIEW.value,
        )
        _, cert_clean, _, _ = create_sample_certificate(
            session,
            approval_status=ApprovalStatus.DRAFT.value,
            doc_status=ProcessingStatus.SUCCEEDED.value,
        )
        session.commit()
        review_id = cert_review.id
        clean_id = cert_clean.id

    res = client.get("/api/v1/document-reviews")
    assert res.status_code == 200
    items = res.json()["data"]
    cert_ids = [item["certificate_id"] for item in items]
    assert review_id in cert_ids
    assert clean_id not in cert_ids

    review_item = next(item for item in items if item["certificate_id"] == review_id)
    assert review_item["blocking_issues_count"] >= 1
    assert review_item["quality_score"] < 1.0
    assert any(i["code"] == "missing_required_field" for i in review_item["issues_summary"])


def test_reprocess_stages(review_settings: Settings):
    app = create_app(review_settings)
    client = TestClient(app)

    with app.state.sessions() as session:
        _, cert, _, _ = create_sample_certificate(session)
        session.commit()
        cert_id = cert.id

    # 1. Reprocess from normalization
    res_norm = client.post(
        f"/api/v1/certificates/{cert_id}/reprocess",
        json={
            "from_stage": "normalization",
            "person_name": "Auditor Calidad",
            "reason": "Re-validar reglas tras actualización",
        },
    )
    assert res_norm.status_code == 200
    norm_data = res_norm.json()["data"]
    assert norm_data["stage"] == "normalization"
    assert norm_data["status"] == "evaluated"
    assert norm_data["quality_report"]["status"] == "clean"

    # 2. Reprocess from extraction (enqueues job)
    res_ext = client.post(
        f"/api/v1/certificates/{cert_id}/reprocess",
        json={
            "from_stage": "extraction",
            "person_name": "Ingeniero OCR",
            "reason": "Re-extraer con nuevo modelo de layout",
        },
    )
    assert res_ext.status_code == 200
    ext_data = res_ext.json()["data"]
    assert ext_data["stage"] == "extraction"
    assert ext_data["status"] == "queued"
    assert ext_data["job_id"] is not None

    # 3. Reprocess from classification (enqueues reclassification job)
    res_cls = client.post(
        f"/api/v1/certificates/{cert_id}/reprocess",
        json={
            "from_stage": "classification",
            "person_name": "Agente Aduanal",
            "reason": "Re-clasificar conforme a nuevo catálogo",
        },
    )
    assert res_cls.status_code == 200
    cls_data = res_cls.json()["data"]
    assert cls_data["stage"] == "classification"
    assert cls_data["status"] == "queued"
    assert cls_data["job_id"] is not None

    # 4. Invalid stage validation
    res_inv = client.post(
        f"/api/v1/certificates/{cert_id}/reprocess",
        json={
            "from_stage": "invalid_stage",
            "person_name": "Test",
            "reason": "Invalid",
        },
    )
    assert res_inv.status_code == 422


def test_quality_gating_and_manual_correction_flow(review_settings: Settings):
    app = create_app(review_settings)
    client = TestClient(app)

    with app.state.sessions() as session:
        # Create certificate with low confidence thickness (0.45 < 0.70 threshold)
        doc, cert, prod, heat = create_sample_certificate(
            session,
            thickness=Decimal("2.50"),
            thickness_confidence=0.45,  # Low confidence
        )
        session.commit()
        cert_id = cert.id
        prod_id = prod.id

    # 1. Inspect quality report: contains low_confidence_field blocking issue
    res_rep = client.get(f"/api/v1/certificates/{cert_id}/quality-report")
    assert res_rep.status_code == 200
    report_data = res_rep.json()["data"]
    assert report_data["status"] == "needs_review"
    assert report_data["blocking_count"] >= 1
    assert any(i["code"] == "low_confidence_field" for i in report_data["issues"])

    # 2. Classification service respects gating: outcome must be needs_review, no guessed fraction/nico
    with app.state.sessions() as session:
        rule_set = session.scalar(select(RuleSet).order_by(RuleSet.id).limit(1))
        assert rule_set is not None
        cls_service = ClassificationService(review_settings)
        run = cls_service.classify_certificate(
            session,
            certificate_id=cert_id,
            person_name="Validador Inicial",
            reason="Prueba de compuerta de calidad",
        )
        session.commit()
        run_id = run.id

    # Check classification results
    res_run = client.get(f"/api/v1/classification-runs/{run_id}")
    assert res_run.status_code == 200
    run_detail = res_run.json()["data"]
    res_item = run_detail["results"][0]
    assert res_item["outcome"] == "needs_review"
    assert res_item["fraction"] is None
    assert res_item["nico"] is None
    assert len(res_item["candidates"]) == 0
    assert len(res_item["details"]["quality_issues"]) >= 1

    # 3. User corrects the observation manually via ReviewService
    with app.state.sessions() as session:
        obs = session.scalar(
            select(Observation).where(
                Observation.certificate_id == cert_id,
                Observation.product_id == prod_id,
                Observation.field_path == "thickness_mm",
                Observation.is_current.is_(True),
            )
        )
        assert obs is not None
        obs_id = obs.id

    res_corr = client.post(
        f"/api/v1/observations/{obs_id}/corrections",
        json={
            "normalized_value": 2.50,
            "raw_value": "2.50 mm",
            "unit": "mm",
            "person_name": "Perito Metalúrgico",
            "reason": "Confirmación visual en certificado físico",
        },
    )
    assert res_corr.status_code == 200
    new_obs_id = res_corr.json()["data"]["observation_id"]
    with app.state.sessions() as session:
        new_obs = session.get(Observation, new_obs_id)
        assert new_obs is not None
        assert new_obs.confidence == 1.0
        assert new_obs.is_current is True
        assert new_obs.supersedes_id == obs_id

    # 4. Reprocess from normalization: report now evaluates to clean
    res_reprocess = client.post(
        f"/api/v1/certificates/{cert_id}/reprocess",
        json={
            "from_stage": "normalization",
            "person_name": "Perito Metalúrgico",
            "reason": "Re-evaluar tras corrección de espesor",
        },
    )
    assert res_reprocess.status_code == 200
    updated_report = res_reprocess.json()["data"]["quality_report"]
    assert updated_report["status"] == "clean"
    assert updated_report["blocking_count"] == 0

    # 5. Reclassification now proceeds normally through the classification engine!
    with app.state.sessions() as session:
        run2 = cls_service.classify_certificate(
            session,
            certificate_id=cert_id,
            person_name="Validador Posterior",
            reason="Reclasificación post corrección",
        )
        session.commit()
        run2_id = run2.id

    res_run2 = client.get(f"/api/v1/classification-runs/{run2_id}")
    assert res_run2.status_code == 200
    run2_detail = res_run2.json()["data"]
    res2_item = run2_detail["results"][0]
    assert res2_item["details"]["document_quality_status"] == "clean"
    assert len(res2_item["details"]["quality_issues"]) == 0
    assert "7208" in res2_item["details"]["candidates"]


