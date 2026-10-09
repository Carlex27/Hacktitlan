from __future__ import annotations

from io import BytesIO
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from backend.app.api.app import create_app, serialize_candidate_factor
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
    assert "/api/v1/classification-candidates/{candidate_id}" in schema["paths"]
    assert "/api/v1/classification-results/{result_id}/select" in schema["paths"]
    assert "/api/v1/classification-runs/{run_id}/approve" in schema["paths"]
    assert "/api/v1/ocr/status" in schema["paths"]
    assert "/api/v1/ocr/models" in schema["paths"]
    assert "/api/v1/ocr/smoke-check" in schema["paths"]

    schemas = schema["components"]["schemas"]
    assert "CandidateFactorRead" in schemas
    factor_props = schemas["CandidateFactorRead"]["properties"]
    for field in (
        "id", "sequence", "rule_code", "outcome", "operator",
        "expected", "observed", "unit", "explanation", "required_for_selection", "evidence_links"
    ):
        assert field in factor_props

    assert "CandidateDetailRead" in schemas
    detail_props = schemas["CandidateDetailRead"]["properties"]
    for field in (
        "id", "classification_result_id", "rank", "fraction",
        "nico", "description", "support_level", "details", "factors"
    ):
        assert field in detail_props

    assert "CandidateSelectionRead" in schemas
    select_props = schemas["CandidateSelectionRead"]["properties"]
    for field in (
        "selection_id", "classification_result_id", "candidate_id",
        "fraction", "nico", "person_name", "reason", "workstation_name", "created_at"
    ):
        assert field in select_props

    candidate_responses = schema["paths"]["/api/v1/classification-candidates/{candidate_id}"]["get"]["responses"]
    assert "200" in candidate_responses and "404" in candidate_responses

    select_responses = schema["paths"]["/api/v1/classification-results/{result_id}/select"]["post"]["responses"]
    assert "200" in select_responses and "404" in select_responses and "409" in select_responses

    approve_responses = schema["paths"]["/api/v1/classification-runs/{run_id}/approve"]["post"]["responses"]
    assert "200" in approve_responses and "404" in approve_responses and "409" in approve_responses


def test_candidate_factor_transport_keeps_rule_values_and_evidence():
    factor = SimpleNamespace(
        id=7,
        sequence=2,
        rule_code="chapter72.nico.72255091.08",
        outcome="unknown",
        operator="catalog_qualifier",
        expected_json={"high_speed_steel": True},
        observed_json={"high_speed_steel": None},
        unit=None,
        explanation="Debe verificarse",
        required_for_selection=True,
    )

    payload = serialize_candidate_factor(factor, [{"id": 12}])

    assert payload["expected"] == {"high_speed_steel": True}
    assert payload["observed"] == {"high_speed_steel": None}
    assert payload["evidence_links"] == [{"id": 12}]


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
    assert len(Base.metadata.tables) == 26
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


def test_chemical_factor_evidence_links_only_target_element_observations():
    evidence = [
        {"observation_id": 10, "field_path": "composition_pct.C", "page_number": 1, "bbox": {"x0": 5}, "product_id": 1},
        {"observation_id": 11, "field_path": "composition_pct.Si", "page_number": 1, "bbox": {"x0": 15}, "product_id": 1},
        {"observation_id": 12, "field_path": "composition_pct.Mn", "page_number": 1, "bbox": {"x0": 25}, "product_id": 1},
        {"observation_id": 13, "field_path": "composition_pct.Ti", "page_number": 1, "bbox": {"x0": 35}, "product_id": 1},
        {"observation_id": 14, "field_path": "composition_pct.B", "page_number": 1, "bbox": {"x0": 45}, "product_id": 1},
    ]

    ti_evidence = ClassificationService._step_evidence(evidence, ("composition_pct.Ti",))
    assert len(ti_evidence) == 1
    assert ti_evidence[0]["observation_id"] == 13
    assert ti_evidence[0]["field_path"] == "composition_pct.Ti"

    c_evidence = ClassificationService._step_evidence(evidence, ("composition_pct.C",))
    assert len(c_evidence) == 1
    assert c_evidence[0]["observation_id"] == 10
    assert c_evidence[0]["field_path"] == "composition_pct.C"


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


def test_ocr_api_endpoints_return_structured_responses(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "backend.app.api.app.run_smoke_check",
        lambda _settings: {"success": False, "error": "runtime unavailable"},
    )
    settings = Settings(
        storage_root=tmp_path / "storage",
        model_root=tmp_path / "models",
        database_url="postgresql+psycopg://user:pass@localhost/test",
    )
    with TestClient(create_app(settings)) as client:
        status_res = client.get("/api/v1/ocr/status")
        models_res = client.get("/api/v1/ocr/models")
        smoke_res = client.post("/api/v1/ocr/smoke-check")

    assert status_res.status_code == 200
    assert "data" in status_res.json()
    assert "models" in status_res.json()["data"]

    assert models_res.status_code == 200
    assert models_res.json()["data"]["status"] == "not_installed"

    assert smoke_res.status_code == 200
    assert smoke_res.json()["data"]["success"] is False  # not installed in test env
