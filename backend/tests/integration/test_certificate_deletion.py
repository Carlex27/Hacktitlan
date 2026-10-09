import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text

from backend.app.api.app import create_app
from backend.app.application.certificate_extraction import CertificateExtractionService
from backend.app.application.worker import Worker
from backend.app.infrastructure.database.models import (
    ApprovalEvent, ClassificationCandidate, ClassificationRun, ClassificationSelection,
    Correction, Document, Job, MillCertificate, Observation, StoredFile,
)
from backend.app.infrastructure.database.session import create_session_factory
from backend.app.infrastructure.files import FileStorage
from backend.tests.integration.test_document_processing_flow import (
    FIXTURE, StaticExtractor, processing_settings, upload,
)


def test_delete_processed_certificate_and_reupload(processing_settings):
    settings = processing_settings
    sessions = create_session_factory(settings)
    storage = FileStorage(settings.storage_root, settings.max_pdf_bytes)
    normalized = CertificateExtractionService.normalize_known_payload(json.loads(FIXTURE.read_text(encoding="utf-8")))
    extractor = StaticExtractor({
        "status": "extracted", "document": {"page_count": 1},
        "detection": {"kind": "mill_certificate", "confidence": 1.0, "signals": []},
        "field_candidates": [], "table_candidates": [], "adapter": "test",
        "certificate": normalized,
    })
    with TestClient(create_app(settings)) as client:
        created = upload(client)
        assert Worker(settings, sessions, storage, extractor=extractor).run_once()
        other = upload(client, b"%PDF-1.7\nother")
        with sessions.begin() as session:
            run = session.scalar(select(ClassificationRun))
            child = ClassificationRun(certificate_id=created["certificate_id"],
                                      rule_set_id=run.rule_set_id, parent_run_id=run.id,
                                      input_snapshot_json={}, demo_notice=settings.demo_notice)
            session.add(child)
            candidate = session.scalar(select(ClassificationCandidate))
            first = ClassificationSelection(classification_result_id=candidate.classification_result_id,
                                            candidate_id=candidate.id, person_name="Test",
                                            reason="Test", workstation_name="Test")
            session.add(first)
            session.flush()
            session.add(ClassificationSelection(classification_result_id=candidate.classification_result_id,
                                                candidate_id=candidate.id, supersedes_selection_id=first.id,
                                                person_name="Test", reason="Test", workstation_name="Test"))
            session.add(ApprovalEvent(classification_run_id=run.id, from_status="draft",
                                      to_status="needs_review", person_name="Test", reason="Test",
                                      workstation_name="Test"))
            previous = session.scalar(select(Observation))
            replacement = Observation(certificate_id=created["certificate_id"], field_path=previous.field_path,
                                      supersedes_id=previous.id, normalized_value_json="test")
            session.add(replacement)
            session.flush()
            session.add(Correction(certificate_id=created["certificate_id"], previous_observation_id=previous.id,
                                   replacement_observation_id=replacement.id, person_name="Test",
                                   reason="Test", workstation_name="Test"))
        export_response = client.post("/api/v1/exports", json={
            "certificate_ids": [created["certificate_id"]], "person_name": "Test",
        })
        assert export_response.status_code == 202, export_response.text
        export = export_response.json()["data"]
        # Procesar primero el otro documento en cola y luego el reporte.
        worker = Worker(settings, sessions, storage, extractor=StaticExtractor({
            "status": "needs_review", "document": {"page_count": 1},
            "detection": {}, "field_candidates": [], "table_candidates": [],
        }))
        assert worker.run_once()
        assert worker.run_once()
        assert client.get(f"/api/v1/exports/{export['export_id']}").json()["data"]["status"] == "succeeded"
        with sessions() as session:
            document = session.get(Document, created["document_id"])
            source = storage.resolve(session.get(StoredFile, document.stored_file_id).relative_path)
            assert session.scalar(text("SELECT count(*) FROM classification_results")) > 0
        response = client.delete(f"/api/v1/certificates/{created['certificate_id']}")
        assert response.status_code == 200, response.text
        assert response.json()["data"] == {
            "certificate_id": created["certificate_id"], "document_id": created["document_id"], "deleted": True,
        }
        assert not source.exists()
        assert client.get(f"/api/v1/certificates/{other['certificate_id']}").status_code == 200
        assert client.get(f"/api/v1/documents/{created['document_id']}/file").status_code == 404
        assert client.get(f"/api/v1/jobs/{created['job_id']}").status_code == 404
        assert client.get(f"/api/v1/exports/{export['export_id']}").status_code == 404
        assert client.get(f"/api/v1/jobs/{export['job_id']}").status_code == 404
        assert client.delete(f"/api/v1/certificates/{created['certificate_id']}").status_code == 404
        with sessions() as session:
            for table in ("heats", "products", "observations", "chemical_compositions", "extraction_runs",
                          "classification_runs", "classification_results", "classification_candidates",
                          "candidate_factors", "decision_steps", "evidence_links", "corrections", "approval_events",
                          "classification_selections", "exports"):
                if table == "extraction_runs":
                    assert session.scalar(text("SELECT count(*) FROM extraction_runs WHERE document_id = :id"),
                                          {"id": created["document_id"]}) == 0
                    continue
                assert session.scalar(text(f"SELECT count(*) FROM {table}")) == 0
            assert session.scalar(text("SELECT count(*) FROM rule_sets")) > 0
        replacement = upload(client)
        assert replacement["duplicate"] is False
        assert replacement["certificate_id"] != created["certificate_id"]


@pytest.mark.parametrize("export_job", [False, True])
def test_running_job_blocks_deletion(processing_settings, export_job):
    sessions = create_session_factory(processing_settings)
    with TestClient(create_app(processing_settings)) as client:
        created = upload(client)
        job_id = created["job_id"]
        if export_job:
            from backend.app.infrastructure.database.models import Export
            with sessions.begin() as session:
                export = Export(format="xlsx", status="running", person_name="Test", workstation_name="Test",
                                scope_json={"certificate_ids": [created["certificate_id"]]})
                session.add(export)
                session.flush()
                job = Job(kind="export_xlsx", status="running", payload_json={"export_id": export.id})
                session.add(job)
                session.flush()
                job_id = job.id
        with sessions.begin() as session:
            session.get(Job, job_id).status = "running"
        response = client.delete(f"/api/v1/certificates/{created['certificate_id']}")
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "certificate_in_use"
        assert client.get(f"/api/v1/certificates/{created['certificate_id']}").status_code == 200


@pytest.mark.parametrize("failure", ["storage", "commit"])
def test_failure_rolls_back(processing_settings, monkeypatch, failure):
    sessions = create_session_factory(processing_settings)
    with TestClient(create_app(processing_settings)) as client:
        created = upload(client)
        with sessions() as session:
            document = session.get(Document, created["document_id"])
            storage = FileStorage(processing_settings.storage_root, processing_settings.max_pdf_bytes)
            source = storage.resolve(session.get(StoredFile, document.stored_file_id).relative_path)
        def fail(*args):
            raise OSError("Storage unavailable")
        if failure == "storage":
            monkeypatch.setattr("pathlib.Path.replace", fail)
        else:
            monkeypatch.setattr("sqlalchemy.orm.Session.commit", fail)
        with pytest.raises(OSError):
            client.delete(f"/api/v1/certificates/{created['certificate_id']}")
        with sessions() as session:
            assert session.get(MillCertificate, created["certificate_id"]) is not None
            assert session.get(Job, created["job_id"]) is not None
        assert source.read_bytes() == b"%PDF-1.7\nfixture"


@pytest.mark.parametrize("missing_file", [False, True])
def test_queued_deletion_preserves_shared_file_and_revision(processing_settings, missing_file):
    sessions = create_session_factory(processing_settings)
    storage = FileStorage(processing_settings.storage_root, processing_settings.max_pdf_bytes)
    with TestClient(create_app(processing_settings)) as client:
        created = upload(client)
        with sessions.begin() as session:
            document = session.get(Document, created["document_id"])
            stored_id = document.stored_file_id
            source = storage.resolve(session.get(StoredFile, stored_id).relative_path)
            if missing_file:
                source.unlink()
            else:
                shared = Document(stored_file_id=stored_id)
                session.add(shared)
                session.flush()
                revision = MillCertificate(document_id=shared.id, previous_revision_id=created["certificate_id"],
                                           revision_number=2, demo_notice=processing_settings.demo_notice)
                session.add(revision)
                session.flush()
                revision_id = revision.id
        response = client.delete(f"/api/v1/certificates/{created['certificate_id']}")
        assert response.status_code == 200, response.text
        with sessions() as session:
            assert session.get(Job, created["job_id"]) is None
            if missing_file:
                assert session.get(StoredFile, stored_id) is None
            else:
                assert source.exists()
                assert session.get(StoredFile, stored_id) is not None
                assert session.get(MillCertificate, revision_id).previous_revision_id is None


def test_production_disabled_and_openapi(processing_settings):
    settings = processing_settings.model_copy(update={"environment": "production"})
    with TestClient(create_app(settings)) as client:
        response = client.delete("/api/v1/certificates/1")
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "certificate_deletion_disabled"
        operation = client.get("/openapi.json").json()["paths"]["/api/v1/certificates/{certificate_id}"]["delete"]
        assert "requestBody" not in operation
        assert {"200", "403", "404", "409"} <= operation["responses"].keys()
