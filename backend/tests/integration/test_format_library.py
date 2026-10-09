from dataclasses import replace
from hashlib import sha256

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text

from backend.app.api.app import create_app
from backend.app.application.worker import Worker
from backend.app.infrastructure.database.models import Document, Job, PreparedDocumentLayout, CertificateFormatTest
from backend.app.infrastructure.files import FileStorage
from backend.tests.integration.test_document_processing_flow import processing_settings, upload, StaticExtractor
from backend.tests.unit.test_format_templates import configuration, layout

ACTOR = {"person_name": "Operador de pruebas", "reason": "Validar el nuevo formato"}


@pytest.fixture
def client(processing_settings):
    with TestClient(create_app(processing_settings)) as client:
        with client.app.state.sessions.begin() as session:
            session.execute(text("TRUNCATE certificate_formats RESTART IDENTITY CASCADE"))
        yield client


def uploaded(client):
    ids = upload(client)
    assert client.post(f"/api/v1/jobs/{ids['job_id']}/cancel", json=ACTOR).status_code == 200
    return ids


class Reader:
    def __init__(self, client=None, cancel_job=None, fail=False):
        self.client, self.cancel_job, self.fail = client, cancel_job, fail
        self.released = False

    def read(self, path, page_callback, cancel_check):
        if self.fail:
            raise RuntimeError("Fallo controlado de OCR")
        page_callback(1, 1)
        if self.cancel_job:
            assert self.client.post(f"/api/v1/jobs/{self.cancel_job}/cancel", json=ACTOR).status_code == 200
            assert cancel_check()
        return replace(layout(), file_name=path.name, sha256=sha256(path.read_bytes()).hexdigest())

    def release(self):
        self.released = True


def worker(client, settings, reader):
    return Worker(settings, client.app.state.sessions, FileStorage(settings.storage_root, settings.max_pdf_bytes),
                  extractor=StaticExtractor({}), layout_reader=reader)


def draft(client):
    response = client.post("/api/v1/certificate-formats", json={**ACTOR, "name": "Formato piloto"})
    assert response.status_code == 201, response.text
    detail = client.get(f"/api/v1/certificate-formats/{response.json()['data']['id']}").json()["data"]
    initial = detail["versions"][0]
    edit = client.patch(f"/api/v1/certificate-format-versions/{initial['id']}", json={
        **ACTOR, "expected_revision": 1, "configuration": configuration().model_dump(mode="json")})
    assert edit.status_code == 200, edit.text
    return edit.json()["data"]


def prepare(client, settings, ids):
    response = client.post(f"/api/v1/documents/{ids['document_id']}/layout-jobs", json=ACTOR)
    assert response.status_code == 202, response.text
    reader = Reader()
    assert worker(client, settings, reader).run_once()
    assert reader.released
    job = client.get(f"/api/v1/jobs/{response.json()['data']['job_id']}").json()["data"]
    assert job["status"] == "succeeded" and job["progress"] == 100
    response = client.get(f"/api/v1/documents/{ids['document_id']}/layout")
    assert response.status_code == 200, response.text
    return response.json()["data"]


def test_draft_layout_and_preview_flow_preserves_certificate_and_exact_revision(client, processing_settings):
    ids = uploaded(client)
    version = draft(client)
    prepared = prepare(client, processing_settings, ids)
    response = client.post("/api/v1/documents", files={"file": ("certificate.pdf", b"%PDF-1.7\nfixture", "application/pdf")})
    assert response.status_code == 200
    duplicate = response.json()["data"]
    assert duplicate["duplicate"] and duplicate["job_id"] == ids["job_id"]
    assert prepared["document"]["file_name"] == "certificate.pdf"
    request = {**ACTOR, "layout_id": prepared["id"], "expected_revision": version["revision"]}
    created = client.post(f"/api/v1/certificate-format-versions/{version['id']}/tests", json=request)
    assert created.status_code == 202, created.text
    test = created.json()["data"]
    # Editing the draft cannot modify an already queued preview.
    edit = client.patch(f"/api/v1/certificate-format-versions/{version['id']}", json={
        **ACTOR, "expected_revision": version["revision"], "configuration": {}})
    assert edit.status_code == 200
    assert worker(client, processing_settings, Reader(fail=True)).run_once()  # Uses cached layout, not reader.
    result = client.get(f"/api/v1/certificate-format-tests/{test['id']}").json()["data"]
    assert result["status"] == "succeeded" and not result["current_revision"]
    assert result["revision"] == version["revision"]
    assert result["configuration_sha256"] == version["configuration_sha256"]
    assert result["result"]["certificate"]["products"][0]["composition_pct"]["C"] == .0013
    certificate = client.get(f"/api/v1/certificates/{ids['certificate_id']}").json()["data"]
    assert certificate["products"] == []
    with client.app.state.sessions() as session:
        assert session.get(Document, ids["document_id"]).processing_status == "queued"
    stale = client.post(f"/api/v1/certificate-format-versions/{version['id']}/tests", json=request)
    assert stale.status_code == 409 and stale.json()["error"]["code"] == "format_revision_conflict"


def test_edit_conflicts_unknown_configuration_and_missing_layout(client):
    ids = uploaded(client)
    assert client.get(f"/api/v1/documents/{ids['document_id']}/layout").status_code == 409
    version = draft(client)
    url = f"/api/v1/certificate-format-versions/{version['id']}"
    response = client.patch(url, json={**ACTOR, "expected_revision": 1, "configuration": {}})
    assert response.status_code == 409
    assert client.patch(url, json={**ACTOR, "expected_revision": 2, "configuration": {"script": "run"}}).status_code == 422
    assert client.post("/api/v1/certificate-formats", json={**ACTOR, "name": "   "}).status_code == 422
    assert client.post(url + "/tests", json={**ACTOR, "expected_revision": 2, "layout_id": 999999}).status_code == 404
    assert client.get("/api/v1/certificate-format-versions/999999").status_code == 404
    formats = client.get("/api/v1/certificate-formats?limit=1&offset=0").json()["data"]
    assert len(formats) == 1
    assert len(client.get("/api/v1/certificate-formats?q=piloto").json()["data"]) == 1
    assert client.get("/api/v1/certificate-formats?q=%25").json()["data"] == []


def test_cancel_running_layout_does_not_save_partial_data(client, processing_settings):
    ids = uploaded(client)
    response = client.post(f"/api/v1/documents/{ids['document_id']}/layout-jobs", json=ACTOR)
    job_id = response.json()["data"]["job_id"]
    reader = Reader(client, job_id)
    assert worker(client, processing_settings, reader).run_once()
    result = client.get(f"/api/v1/jobs/{job_id}").json()["data"]
    assert result["status"] == "cancelled" and reader.released
    assert client.get(f"/api/v1/documents/{ids['document_id']}/layout").status_code == 409


def test_layout_failure_retries_then_is_error_not_review(client, processing_settings):
    ids = uploaded(client)
    response = client.post(f"/api/v1/documents/{ids['document_id']}/layout-jobs", json=ACTOR)
    job_id = response.json()["data"]["job_id"]
    runner = worker(client, processing_settings, Reader(fail=True))
    for _ in range(3):
        assert runner.run_once()
    result = client.get(f"/api/v1/jobs/{job_id}").json()["data"]
    assert result["status"] == "failed" and result["error_code"] == "RuntimeError"
    assert client.get(f"/api/v1/documents/{ids['document_id']}/layout").status_code == 409


def test_image_uses_cached_orientation_and_rejects_mismatch(client, processing_settings, monkeypatch):
    ids = uploaded(client)
    prepared = prepare(client, processing_settings, ids)
    called = []
    def render(path, page_number, *, rotation, expected_size):
        called.append((page_number, rotation, expected_size))
        return b"png fixture"
    monkeypatch.setattr("backend.app.api.format_routes.render_page_image", render)
    response = client.get(f"/api/v1/document-layouts/{prepared['id']}/pages/1/image")
    assert response.status_code == 200 and response.headers["content-type"] == "image/png"
    assert called == [(1, 0, (100, 100))]
    assert client.get(f"/api/v1/document-layouts/{prepared['id']}/pages/2/image").status_code == 404
    def bad_render(*args, **kwargs):
        raise ValueError("Dimensiones incompatibles")
    monkeypatch.setattr("backend.app.api.format_routes.render_page_image", bad_render)
    response = client.get(f"/api/v1/document-layouts/{prepared['id']}/pages/1/image")
    assert response.status_code == 409 and response.json()["error"]["code"] == "layout_image_incompatible"


def test_deletion_removes_owned_layouts_and_tests_but_preserves_format(client, processing_settings):
    ids = uploaded(client)
    version = draft(client)
    prepared = prepare(client, processing_settings, ids)
    created = client.post(f"/api/v1/certificate-format-versions/{version['id']}/tests", json={
        **ACTOR, "expected_revision": version["revision"], "layout_id": prepared["id"]}).json()["data"]
    assert worker(client, processing_settings, Reader()).run_once()
    assert client.delete(f"/api/v1/certificates/{ids['certificate_id']}").status_code == 200
    assert client.get(f"/api/v1/document-layouts/{prepared['id']}").status_code == 404
    assert client.get(f"/api/v1/certificate-format-tests/{created['id']}").status_code == 404
    assert client.get(f"/api/v1/certificate-format-versions/{version['id']}").status_code == 200


def test_openapi_and_cors_document_drafts_and_patch(client):
    spec = client.get("/openapi.json").json()
    assert "patch" in spec["paths"]["/api/v1/certificate-format-versions/{version_id}"]
    assert "post" in spec["paths"]["/api/v1/documents/{document_id}/layout-jobs"]
    assert "post" in spec["paths"]["/api/v1/certificate-format-versions/{version_id}/activate"]
    response = client.options("/api/v1/certificate-format-versions/1", headers={
        "Origin": client.app.state.settings.cors_origins[0], "Access-Control-Request-Method": "PATCH"})
    assert response.status_code == 200 and "PATCH" in response.headers["access-control-allow-methods"]
