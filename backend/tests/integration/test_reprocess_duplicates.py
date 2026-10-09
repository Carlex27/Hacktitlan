from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from backend.app.api.app import create_app
from backend.app.infrastructure.database.models import Job, MillCertificate
from backend.tests.integration.test_document_quality_and_review import (
    create_sample_certificate,
    review_settings,
)


def test_reprocess_blocks_active_pdf_and_queue_only_shows_latest(review_settings):
    app = create_app(review_settings)
    client = TestClient(app)
    with app.state.sessions() as session:
        _, certificate, _, _ = create_sample_certificate(session)
        original_id = certificate.id
        session.commit()
    payload = {"from_stage": "extraction", "person_name": "Test", "reason": "Nuevo OCR"}
    first = client.post(f"/api/v1/certificates/{original_id}/reprocess", json=payload).json()["data"]
    for certificate_id in (original_id, first["certificate_id"]):
        duplicate = client.post(f"/api/v1/certificates/{certificate_id}/reprocess", json=payload)
        assert duplicate.status_code == 409
        assert duplicate.json()["error"]["code"] == "reprocess_in_progress"
        assert duplicate.json()["error"]["details"]["job_id"] == first["job_id"]
    queue = client.get("/api/v1/document-reviews").json()["data"]
    assert [item["certificate_id"] for item in queue] == [first["certificate_id"]]
    assert queue[0]["can_reprocess"] is False
    assert queue[0]["active_job_id"] == first["job_id"]
    with app.state.sessions() as session:
        assert session.scalar(select(func.count(Job.id))) == 1
        job = session.get(Job, first["job_id"])
        job.status = "failed"
        session.commit()
    retry = client.post(f"/api/v1/certificates/{original_id}/reprocess", json=payload)
    assert retry.status_code == 200
    with app.state.sessions() as session:
        latest = session.get(MillCertificate, retry.json()["data"]["certificate_id"])
        assert latest.previous_revision_id == first["certificate_id"]
        assert latest.revision_number == 3


def test_concurrent_requests_create_only_one_extraction(review_settings):
    app = create_app(review_settings)
    with app.state.sessions() as session:
        _, certificate, _, _ = create_sample_certificate(session)
        certificate_id = certificate.id
        session.commit()
    barrier = Barrier(2)

    def request():
        client = TestClient(app)
        barrier.wait(timeout=10)
        return client.post(
            f"/api/v1/certificates/{certificate_id}/reprocess",
            json={"from_stage": "extraction", "person_name": "Test", "reason": "Concurrente"},
        ).status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(lambda _: request(), range(2))) == [200, 409]
    with app.state.sessions() as session:
        assert session.scalar(select(func.count(Job.id))) == 1
