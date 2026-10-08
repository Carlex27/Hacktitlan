from __future__ import annotations

import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from backend.app.application.review_service import ReviewService
from backend.app.config import Settings
from backend.app.domain.enums import ApprovalStatus
from backend.app.infrastructure.database.models import (
    ClassificationCandidate,
    ClassificationResult,
    ClassificationRun,
    ClassificationSelection,
    Document,
    MillCertificate,
    Product,
    RuleSet,
    StoredFile,
)


@pytest.fixture()
def database_url() -> str:
    value = os.getenv("HACKTITLAN_TEST_DATABASE_URL") or Settings().test_database_url
    if not value:
        pytest.skip("Requires the explicit hacktitlan_test PostgreSQL database")
    assert value.rsplit("/", 1)[-1].split("?", 1)[0] == "hacktitlan_test"
    return value


def test_selection_is_audited_and_required_before_approval(database_url: str):
    engine = create_engine(database_url)
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    try:
        token = uuid4().hex
        stored_file = StoredFile(
            sha256=token.ljust(64, "0"),
            original_name="candidate-test.pdf",
            storage_name=f"{token}.pdf",
            relative_path=f"test/{token}.pdf",
            media_type="application/pdf",
            size_bytes=1,
        )
        session.add(stored_file)
        session.flush()
        document = Document(stored_file_id=stored_file.id)
        session.add(document)
        session.flush()
        certificate = MillCertificate(
            document_id=document.id,
            certificate_no=f"TEST-{token}",
            demo_notice="DEMOSTRACIÓN — SIN VALIDEZ ADUANERA",
        )
        session.add(certificate)
        session.flush()
        product = Product(
            certificate_id=certificate.id,
            product_identifier=f"COIL-{token}",
        )
        session.add(product)
        session.flush()
        rule_set = session.scalar(select(RuleSet).order_by(RuleSet.id).limit(1))
        assert rule_set is not None
        run = ClassificationRun(
            certificate_id=certificate.id,
            rule_set_id=rule_set.id,
            approval_status=ApprovalStatus.NEEDS_REVIEW.value,
            input_snapshot_json={},
            demo_notice="DEMOSTRACIÓN — SIN VALIDEZ ADUANERA",
        )
        session.add(run)
        session.flush()
        result = ClassificationResult(
            classification_run_id=run.id,
            product_id=product.id,
            outcome="needs_review",
            details_json={"valid_candidate_count": 3, "selection_required": True},
        )
        session.add(result)
        session.flush()
        candidates = [
            ClassificationCandidate(
                classification_result_id=result.id,
                rank=rank,
                fraction="72091504",
                nico=nico,
                description=f"Opción {nico}",
                support_level="conditional",
                details_json={},
            )
            for rank, nico in enumerate(("01", "02", "03"), start=1)
        ]
        session.add_all(candidates)
        session.flush()

        service = ReviewService(Settings(database_url=database_url))
        first = service.select_classification_candidate(
            session,
            result_id=result.id,
            candidate_id=candidates[1].id,
            person_name="Revisor autorizado",
            reason="La evidencia técnica corresponde a alta resistencia",
        )
        second = service.select_classification_candidate(
            session,
            result_id=result.id,
            candidate_id=candidates[2].id,
            person_name="Revisor autorizado",
            reason="Corrección después de revisar la especificación",
        )

        assert second.supersedes_selection_id == first.id
        assert result.fraction == "72091504"
        assert result.nico == "03"
        assert result.outcome == "classified"
        assert session.scalar(
            select(ClassificationSelection).where(ClassificationSelection.id == first.id)
        ) is first

        service.transition_classification(
            session,
            run_id=run.id,
            target=ApprovalStatus.APPROVED,
            person_name="Aprobador autorizado",
            reason="Clasificación y evidencia verificadas",
        )
        assert run.approval_status == ApprovalStatus.APPROVED.value
    finally:
        session.close()
        transaction.rollback()
        connection.close()
        engine.dispose()
