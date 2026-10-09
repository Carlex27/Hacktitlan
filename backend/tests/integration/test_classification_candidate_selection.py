from __future__ import annotations

import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from backend.app.application.review_service import ReviewService
from backend.app.config import Settings
from backend.app.domain.enums import ApprovalStatus
from backend.app.domain.errors import ConflictError
from backend.app.infrastructure.database.models import (
    CandidateFactor,
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


@pytest.mark.parametrize("factor_outcome", ["matched", "unknown"])
def test_selection_is_audited_and_required_before_approval(database_url: str, factor_outcome: str):
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
        session.add(CandidateFactor(
            candidate_id=candidates[0].id,
            sequence=1,
            rule_code="test.conflict",
            outcome="conflict",
            operator="=",
            expected_json={"value": True},
            observed_json={"value": False},
            explanation="Contradicción de prueba",
            required_for_selection=True,
        ))
        session.flush()

        service = ReviewService(Settings(database_url=database_url))
        with pytest.raises(ConflictError) as conflict:
            service.select_classification_candidate(
                session,
                result_id=result.id,
                candidate_id=candidates[0].id,
                person_name="Revisor autorizado",
                reason="Intento de seleccionar una opción contradictoria",
            )
        assert conflict.value.code == "candidate_has_conflicts"
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

        session.add(CandidateFactor(
            candidate_id=candidates[2].id,
            sequence=1,
            rule_code="test.normative_condition",
            outcome=factor_outcome,
            explanation="Condición normativa revisada",
            required_for_selection=True,
        ))
        session.flush()
        if factor_outcome == "unknown":
            with pytest.raises(ConflictError) as unverified:
                service.transition_classification(
                    session, run_id=run.id, target=ApprovalStatus.APPROVED,
                    person_name="Aprobador autorizado", reason="Condición aún pendiente",
                )
            assert unverified.value.code == "classification_incomplete"
            return

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


def test_candidate_selection_rejects_candidate_from_another_product_or_execution(database_url: str):
    engine = create_engine(database_url)
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    try:
        token = uuid4().hex
        stored_file = StoredFile(
            sha256=token.ljust(64, "0"),
            original_name="candidate-mismatch-test.pdf",
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
        product1 = Product(certificate_id=certificate.id, product_identifier=f"COIL-1-{token}")
        product2 = Product(certificate_id=certificate.id, product_identifier=f"COIL-2-{token}")
        session.add_all([product1, product2])
        session.flush()

        rule_set = session.scalar(select(RuleSet).order_by(RuleSet.id).limit(1))
        assert rule_set is not None

        run1 = ClassificationRun(
            certificate_id=certificate.id,
            rule_set_id=rule_set.id,
            approval_status=ApprovalStatus.NEEDS_REVIEW.value,
            input_snapshot_json={},
            demo_notice="DEMOSTRACIÓN — SIN VALIDEZ ADUANERA",
        )
        run2 = ClassificationRun(
            certificate_id=certificate.id,
            rule_set_id=rule_set.id,
            approval_status=ApprovalStatus.NEEDS_REVIEW.value,
            input_snapshot_json={},
            demo_notice="DEMOSTRACIÓN — SIN VALIDEZ ADUANERA",
        )
        session.add_all([run1, run2])
        session.flush()

        result1 = ClassificationResult(
            classification_run_id=run1.id,
            product_id=product1.id,
            outcome="needs_review",
            details_json={"valid_candidate_count": 3, "selection_required": True},
        )
        result2 = ClassificationResult(
            classification_run_id=run1.id,
            product_id=product2.id,
            outcome="needs_review",
            details_json={"valid_candidate_count": 3, "selection_required": True},
        )
        result_other_run = ClassificationResult(
            classification_run_id=run2.id,
            product_id=product1.id,
            outcome="needs_review",
            details_json={"valid_candidate_count": 3, "selection_required": True},
        )
        session.add_all([result1, result2, result_other_run])
        session.flush()

        candidates_result1 = [
            ClassificationCandidate(
                classification_result_id=result1.id,
                rank=rank,
                fraction="72091504",
                nico=nico,
                description=f"Opción R1-{nico}",
                support_level="fully_supported",
                details_json={},
            )
            for rank, nico in enumerate(("01", "02", "03"), start=1)
        ]
        candidates_result2 = [
            ClassificationCandidate(
                classification_result_id=result2.id,
                rank=rank,
                fraction="72091504",
                nico=nico,
                description=f"Opción R2-{nico}",
                support_level="fully_supported",
                details_json={},
            )
            for rank, nico in enumerate(("01", "02", "03"), start=1)
        ]
        candidates_other_run = [
            ClassificationCandidate(
                classification_result_id=result_other_run.id,
                rank=rank,
                fraction="72091504",
                nico=nico,
                description=f"Opción Run2-{nico}",
                support_level="fully_supported",
                details_json={},
            )
            for rank, nico in enumerate(("01", "02", "03"), start=1)
        ]
        session.add_all(candidates_result1 + candidates_result2 + candidates_other_run)
        session.flush()

        service = ReviewService(Settings(database_url=database_url))

        # Candidate of another product in the same run returns conflict
        with pytest.raises(ConflictError) as conflict_prod:
            service.select_classification_candidate(
                session,
                result_id=result1.id,
                candidate_id=candidates_result2[0].id,
                person_name="Revisor autorizado",
                reason="Intento de cruzar candidatos de otro producto",
            )
        assert conflict_prod.value.code == "candidate_result_mismatch"

        # Candidate of another execution returns conflict
        with pytest.raises(ConflictError) as conflict_run:
            service.select_classification_candidate(
                session,
                result_id=result1.id,
                candidate_id=candidates_other_run[0].id,
                person_name="Revisor autorizado",
                reason="Intento de cruzar candidatos de otra ejecución",
            )
        assert conflict_run.value.code == "candidate_result_mismatch"

        # Non-existent candidate returns conflict
        with pytest.raises(ConflictError) as conflict_missing:
            service.select_classification_candidate(
                session,
                result_id=result1.id,
                candidate_id=999_999,
                person_name="Revisor autorizado",
                reason="Candidato inexistente",
            )
        assert conflict_missing.value.code == "candidate_result_mismatch"
    finally:
        session.close()
        transaction.rollback()
        connection.close()
        engine.dispose()


def test_approval_blocked_if_selected_candidate_has_missing_data_or_conflicts(database_url: str):
    engine = create_engine(database_url)
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    try:
        token = uuid4().hex
        stored_file = StoredFile(
            sha256=token.ljust(64, "0"),
            original_name="candidate-missing-data.pdf",
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
        product = Product(certificate_id=certificate.id, product_identifier=f"COIL-{token}")
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
                support_level="conditional" if rank == 1 else "fully_supported",
                details_json={"missing_fields": ["porcelain_exposed_parts"]} if rank == 1 else {},
            )
            for rank, nico in enumerate(("01", "02", "03"), start=1)
        ]
        session.add_all(candidates)
        session.flush()

        service = ReviewService(Settings(database_url=database_url))
        # Selecting candidate 1 (which has missing fields) succeeds as a selection event
        service.select_classification_candidate(
            session,
            result_id=result.id,
            candidate_id=candidates[0].id,
            person_name="Revisor técnico",
            reason="Seleccionado para revisión posterior",
        )
        assert result.outcome == "classified"

        # But approval must be blocked because mandatory data is missing
        with pytest.raises(ConflictError) as conflict:
            service.transition_classification(
                session,
                run_id=run.id,
                target=ApprovalStatus.APPROVED,
                person_name="Aprobador",
                reason="Intento de aprobación prematura",
            )
        assert conflict.value.code == "classification_incomplete"
    finally:
        session.close()
        transaction.rollback()
        connection.close()
        engine.dispose()
