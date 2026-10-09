import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.api.app import create_app
from backend.app.api.schemas import JobEnvelope
from backend.app.application.certificate_extraction import CertificateExtractionService
from backend.app.application.worker import Worker
from backend.app.infrastructure.files import FileStorage
from backend.app.infrastructure.database.job_repository import JobRepository
from backend.app.infrastructure.database.models import Job
from backend.tests.integration.test_document_processing_flow import processing_settings, upload


@pytest.mark.parametrize("fail_persistence", [False, True])
def test_progress_is_observable_and_100_requires_committed_data(processing_settings, fail_persistence):
    normalized = CertificateExtractionService.normalize_known_payload(json.loads(
        (Path(__file__).parents[3] / "data/samples/molino-1.raw.json").read_text()))
    observed = []
    with TestClient(create_app(processing_settings)) as client:
        ids = upload(client)

        def current():
            response = client.get(f"/api/v1/jobs/{ids['job_id']}")
            return JobEnvelope.model_validate(response.json()).data

        assert current().progress == 0
        spec = client.get("/openapi.json").json()
        assert spec["paths"]["/api/v1/jobs/{job_id}"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith("/JobEnvelope")

        class Extractor:
            def analyze_pdf(self, _path, page_callback, **_kwargs):
                observed.append(current().progress)
                page_callback(1, 2)
                observed.append(current().progress)
                page_callback(0, 2)  # A GPU retry must not move the bar backwards.
                observed.append(current().progress)
                page_callback(2, 2)
                observed.append(current().progress)
                return {"status": "needs_review", "document": {"page_count": 2}, "certificate": normalized}

        sessions = client.app.state.sessions
        worker = Worker(processing_settings, sessions,
                        FileStorage(processing_settings.storage_root, processing_settings.max_pdf_bytes),
                        extractor=Extractor())
        persist = worker.persistence.persist_normalized

        def checked_persist(*args, **kwargs):
            assert current().progress == 95
            assert current().status == "running"
            if fail_persistence:
                raise RuntimeError("Fallo controlado de guardado")
            return persist(*args, **kwargs)

        worker.persistence.persist_normalized = checked_persist
        assert worker.run_once()
        assert observed == [10, 50, 50, 90]
        job = current()
        assert job.progress == (0 if fail_persistence else 100)
        assert job.status == ("queued" if fail_persistence else "needs_review")
        products = client.get(f"/api/v1/certificates/{ids['certificate_id']}").json()["data"]["products"]
        assert len(products) == (0 if fail_persistence else len(normalized["products"]))
        if fail_persistence:
            assert worker.run_once()
            assert worker.run_once()
            assert current().status == "failed"
            assert current().progress == 95
            assert observed == [10, 50, 50, 90] * 3


def test_stale_retry_resets_previous_progress(processing_settings):
    with TestClient(create_app(processing_settings)) as client:
        ids = upload(client)
        with client.app.state.sessions.begin() as session:
            job = session.get(Job, ids["job_id"])
            job.status = "running"
            job.progress = 80
            job.attempts = 1
            job.heartbeat_at = datetime.now(timezone.utc) - timedelta(minutes=10)
            session.flush()
            assert JobRepository().recover_stale(session, 300) == 1
            assert job.status == "queued"
            assert job.progress == 0
