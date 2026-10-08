from __future__ import annotations

from io import BytesIO
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from backend.app.api.app import create_app
from backend.app.api.schemas import ActorReason, CandidateSelectionRequest, ExportRequest
from backend.app.application.document_service import decode_cursor, encode_cursor
from backend.app.application.classification_service import ClassificationService
from backend.app.config import Settings
from backend.app.domain.errors import ApplicationError
from backend.app.infrastructure.files import FileStorage
from backend.app.infrastructure.database.job_repository import JobRepository
from backend.app.application.review_service import ReviewService
from backend.app.infrastructure.database.session import Base
from backend.app.infrastructure.database import models as _models  # noqa: F401
from backend.app.operations.backup import BackupService
from sqlalchemy.dialects import postgresql


def test_cursor_round_trip():
    from datetime import date

    cursor = encode_cursor(date(2026, 10, 7), 123)
    assert decode_cursor(cursor) == (date(2026, 10, 7), 123)


def test_invalid_cursor_is_stable_application_error():
    with pytest.raises(ApplicationError) as error:
        decode_cursor("not-a-cursor")
    assert error.value.code == "invalid_cursor"


def test_storage_is_content_addressed_and_deduplicated(tmp_path):
    storage = FileStorage(tmp_path, 1024)
    first = storage.store_pdf(BytesIO(b"%PDF-1.7\nexample"), "first.pdf")
    second = storage.store_pdf(BytesIO(b"%PDF-1.7\nexample"), "renamed.pdf")

    assert first.sha256 == second.sha256
    assert not first.duplicate
    assert second.duplicate
    assert storage.resolve(first.relative_path).read_bytes() == b"%PDF-1.7\nexample"


def test_storage_rejects_non_pdf_content(tmp_path):
    storage = FileStorage(tmp_path, 1024)
    with pytest.raises(ApplicationError) as error:
        storage.store_pdf(BytesIO(b"not a pdf"), "fake.pdf")
    assert error.value.code == "invalid_pdf"


def test_storage_rejects_path_traversal(tmp_path):
    storage = FileStorage(tmp_path, 1024)
    with pytest.raises(ApplicationError) as error:
        storage.resolve("../outside.pdf")
    assert error.value.code == "invalid_storage_path"


def test_actor_and_reason_must_not_be_blank():
    with pytest.raises(ValueError):
        ActorReason(person_name="  ", reason="because")
    with pytest.raises(ValueError):
        ActorReason(person_name="Ana", reason="  ")


def test_candidate_selection_contract_requires_candidate_actor_and_reason():
    request = CandidateSelectionRequest(
        candidate_id=3,
        person_name="Ana",
        reason="Evidencia técnica revisada",
    )
    assert request.candidate_id == 3
    with pytest.raises(ValueError):
        CandidateSelectionRequest(candidate_id=0, person_name="Ana", reason="Revisión")


def test_live_health_uses_uniform_envelope(tmp_path):
    settings = Settings(storage_root=tmp_path, database_url="postgresql+psycopg://user:pass@localhost/test")
    with TestClient(create_app(settings)) as client:
        response = client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json() == {"data": {"status": "ok"}, "meta": {}, "error": None}


def test_openapi_documents_evidence_navigation_endpoint(tmp_path):
    settings = Settings(
        storage_root=tmp_path,
        database_url="postgresql+psycopg://user:pass@localhost/test",
    )
    with TestClient(create_app(settings)) as client:
        schema = client.get("/openapi.json").json()

    assert "/api/v1/evidence/{evidence_link_id}" in schema["paths"]
    assert "/api/v1/documents/{document_id}/file" in schema["paths"]


def test_empty_secondary_backup_path_is_disabled(monkeypatch):
    monkeypatch.setenv("HACKTITLAN_SECONDARY_BACKUP_ROOT", "")
    assert Settings().secondary_backup_root is None


def test_generated_files_are_stored_by_hash(tmp_path):
    storage = FileStorage(tmp_path / "storage", 1024)
    source = tmp_path / "report.xlsx"
    source.write_bytes(b"generated workbook")
    artifact = storage.store_generated(
        source,
        "classification.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    assert artifact.relative_path.startswith("generated/")
    assert storage.resolve(artifact.relative_path).read_bytes() == source.read_bytes()


def test_job_claim_uses_skip_locked_and_updates_state():
    job = SimpleNamespace(
        status="queued", attempts=0, max_attempts=3, worker_id=None,
        heartbeat_at=None, started_at=None, progress=0,
    )

    class FakeSession:
        statement = None

        def scalar(self, statement):
            self.statement = statement
            return job

        def flush(self):
            pass

    session = FakeSession()
    claimed = JobRepository().claim_next(session, "worker-1")
    sql = str(session.statement.compile(dialect=postgresql.dialect()))
    assert "SKIP LOCKED" in sql
    assert claimed.status == "running"
    assert claimed.attempts == 1
    assert claimed.worker_id == "worker-1"


def test_review_service_requires_person_and_reason():
    with pytest.raises(ApplicationError) as error:
        ReviewService._require_actor_reason("", "missing person")
    assert error.value.code == "audit_fields_required"


def test_manual_chemistry_rejects_invalid_percentage():
    with pytest.raises(ApplicationError) as error:
        ReviewService._validate_normalized("composition_pct.Cr", 101)
    assert error.value.code == "invalid_observation_value"


def test_manual_boolean_does_not_accept_truthy_text():
    with pytest.raises(ApplicationError):
        ReviewService._validate_normalized("pickled", "yes")


def test_export_scope_cannot_be_empty():
    with pytest.raises(ValueError):
        ExportRequest(person_name="Ana")


def test_export_can_target_a_historical_classification_run():
    request = ExportRequest(person_name="Ana", classification_run_ids=[12])
    assert request.classification_run_ids == [12]


def test_all_primary_keys_use_bigint_identity():
    assert len(Base.metadata.tables) == 21
    for table in Base.metadata.tables.values():
        primary_key = list(table.primary_key.columns)
        assert len(primary_key) == 1
        assert primary_key[0].identity is not None


def test_step_evidence_selects_exact_field_and_prefers_coordinates():
    evidence = [
        {
            "observation_id": 1, "field_path": "composition_pct.Ti",
            "page_number": None, "bbox": None, "product_id": 4,
        },
        {
            "observation_id": 2, "field_path": "composition_pct.Ti",
            "page_number": 2, "bbox": {"x0": 10}, "product_id": 4,
        },
        {
            "observation_id": 3, "field_path": "width_mm",
            "page_number": 1, "bbox": {"x0": 20}, "product_id": 4,
        },
    ]

    selected = ClassificationService._step_evidence(evidence, ("composition_pct.Ti",))

    assert [item["observation_id"] for item in selected] == [2]


def test_backup_retention_keeps_seven_daily_files(tmp_path):
    settings = Settings(
        storage_root=tmp_path / "storage",
        backup_root=tmp_path / "backups",
        secondary_backup_root=tmp_path / "secondary",
    )
    settings.backup_root.mkdir()
    for index in range(9):
        path = settings.backup_root / f"backup_daily_202610{index:02d}.zip"
        path.write_bytes(b"backup")
        path.touch()
    BackupService(settings)._apply_retention("daily")
    assert len(list(settings.backup_root.glob("backup_daily_*.zip"))) == 7

