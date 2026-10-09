from dataclasses import replace
from hashlib import sha256
import asyncio
import httpx

from sqlalchemy import select

from backend.app.application.certificate_extraction import CertificateExtractionService
from backend.app.application.worker import Worker
from backend.app.application.format_activation import template_snapshots
from backend.app.domain.document import BoundingBox, TextBlock
from backend.app.infrastructure.database.models import ExtractionRun, Job, Observation
from backend.app.infrastructure.files import FileStorage
from backend.tests.integration.test_format_library import client, draft, worker, ACTOR
from backend.tests.integration.test_document_processing_flow import processing_settings
from backend.tests.unit.test_format_templates import configuration, layout, REGION


def test_format_creation_is_committed_before_response_headers(processing_settings):
    from backend.app.api.app import create_app
    from backend.app.infrastructure.database.models import CertificateFormat
    app = create_app(processing_settings)
    observed = []

    async def wrapped(scope, receive, send):
        async def check_send(message):
            if message["type"] == "http.response.start":
                with app.state.sessions() as session:
                    observed.append(session.scalar(select(CertificateFormat.id).where(CertificateFormat.name == "Commit probe")))
            await send(message)
        await app(scope, receive, check_send)

    async def request():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=wrapped), base_url="http://test") as api:
            response = await api.post("/api/v1/certificate-formats", json={**ACTOR, "name": "Commit probe"})
            assert response.status_code == 201, response.text
    asyncio.run(request())
    assert observed and observed[0] is not None


class RecognitionReader:
    def read(self, path, page_callback=None, cancel_check=None):
        doc = layout()
        page = replace(doc.pages[0], blocks=(TextBlock(1, "Pilot certificate", BoundingBox(1, 1, 90, 4)),
                                             TextBlock(1, "Coil Heat Thickness", BoundingBox(1, 5, 90, 9))))
        return replace(doc, sha256=sha256(path.read_bytes()).hexdigest(), pages=(page,))

    def release(self):
        pass


def upload_pdf(client, number):
    content = f"%PDF-1.7\nfixture {number}".encode()
    result = client.post("/api/v1/documents", files={"file": (f"example-{number}.pdf", content, "application/pdf")}).json()["data"]
    client.post(f"/api/v1/jobs/{result['job_id']}/cancel", json=ACTOR)
    return result


def validated_version(client, settings):
    version = draft(client)
    config = configuration().model_dump(mode="json")
    config["recognition"] = [{"text": text, "region": REGION, "page_number": 1}
                             for text in ("Pilot certificate", "Coil Heat Thickness")]
    response = client.patch(f"/api/v1/certificate-format-versions/{version['id']}", json={
        **ACTOR, "configuration": config, "expected_revision": version["revision"]})
    assert response.status_code == 200, response.text
    version = response.json()["data"]
    ids = []
    runner = worker(client, settings, RecognitionReader())
    for number in range(3):
        uploaded = upload_pdf(client, number)
        ids.append(uploaded)
        response = client.post(f"/api/v1/documents/{uploaded['document_id']}/layout-jobs", json=ACTOR)
        assert response.status_code == 202
        assert runner.run_once()
        prepared = client.get(f"/api/v1/documents/{uploaded['document_id']}/layout").json()["data"]
        response = client.post(f"/api/v1/certificate-format-versions/{version['id']}/tests", json={
            **ACTOR, "expected_revision": version["revision"], "layout_id": prepared["id"]})
        assert response.status_code == 202
        test_id = response.json()["data"]["id"]
        assert client.post(f"/api/v1/certificate-format-tests/{test_id}/confirm", json=ACTOR).status_code == 409
        assert runner.run_once()
        response = client.post(f"/api/v1/certificate-format-tests/{test_id}/confirm", json=ACTOR)
        assert response.status_code == 200, response.text
    return version, ids


def test_activation_snapshot_retirement_and_explicit_revision_preserve_history(client, processing_settings):
    version, ids = validated_version(client, processing_settings)
    url = f"/api/v1/certificate-format-versions/{version['id']}"
    action = {**ACTOR, "expected_revision": version["revision"]}
    response = client.post(url + "/activate", json=action)
    assert response.status_code == 200, response.text
    assert response.json()["data"]["status"] == "active"
    assert client.patch(url, json={**action, "configuration": {}}).status_code == 409
    reprocessed = client.post(f"/api/v1/certificates/{ids[0]['certificate_id']}/reprocess", json={
        **ACTOR, "from_stage": "extraction", "format_version_id": version["id"]})
    assert reprocessed.status_code == 200, reprocessed.text
    revision = reprocessed.json()["data"]
    assert revision["certificate_id"] != ids[0]["certificate_id"]
    with client.app.state.sessions() as session:
        job = session.get(Job, revision["job_id"])
        assert job.payload_json["template_candidates"][0]["configuration_sha256"] == version["configuration_sha256"]
    assert client.post(url + "/retire", json=action).status_code == 200
    assert client.post(f"/api/v1/certificates/{ids[1]['certificate_id']}/reprocess", json={
        **ACTOR, "from_stage": "extraction", "format_version_id": version["id"]}).status_code == 409
    extractor = CertificateExtractionService(RecognitionReader())
    runner = Worker(processing_settings, client.app.state.sessions,
                    FileStorage(processing_settings.storage_root, processing_settings.max_pdf_bytes), extractor=extractor)
    assert runner.run_once()
    with client.app.state.sessions() as session:
        run = session.scalar(select(ExtractionRun).where(ExtractionRun.job_id == revision["job_id"]))
        assert run.adapter_name == "user_template"
        assert run.detection_json["template"]["version_id"] == version["id"]
        observations = session.scalars(select(Observation).where(Observation.certificate_id == revision["certificate_id"],
                                                                Observation.field_path == "thickness_mm")).all()
        assert len(observations) == 2 and all(o.page_number == 1 and o.bbox_json for o in observations)
    old = client.get(f"/api/v1/certificates/{ids[0]['certificate_id']}").json()["data"]
    assert old["products"] == []
    revised = client.get(f"/api/v1/certificates/{revision['certificate_id']}").json()["data"]
    assert len(revised["products"]) == 2
    assert client.get(url).json()["data"]["lifecycle"][-1]["status"] == "retired"


def test_activation_rejects_missing_examples_and_edit_invalidates_review(client, processing_settings):
    version = draft(client)
    url = f"/api/v1/certificate-format-versions/{version['id']}"
    response = client.post(url + "/activate", json={**ACTOR, "expected_revision": version["revision"]})
    assert response.status_code == 409 and response.json()["error"]["code"] == "format_recognition_required"
    version, ids = validated_version(client, processing_settings)
    url = f"/api/v1/certificate-format-versions/{version['id']}"
    config = version["configuration"]
    config["rolling"] = "cold"
    changed = client.patch(url, json={**ACTOR, "expected_revision": version["revision"], "configuration": config}).json()["data"]
    response = client.post(url + "/activate", json={**ACTOR, "expected_revision": changed["revision"]})
    assert response.status_code == 409 and response.json()["error"]["code"] == "format_validation_required"


def test_new_active_version_replaces_previous_and_extractor_change_excludes_it(client, processing_settings, monkeypatch):
    version, ids = validated_version(client, processing_settings)
    action = {**ACTOR, "expected_revision": version["revision"]}
    assert client.post(f"/api/v1/certificate-format-versions/{version['id']}/activate", json=action).status_code == 200
    cloned = client.post(f"/api/v1/certificate-formats/{version['format_id']}/versions", json={
        **ACTOR, "configuration": version["configuration"]}).json()["data"]
    runner = worker(client, processing_settings, RecognitionReader())
    for uploaded in ids:
        prepared = client.get(f"/api/v1/documents/{uploaded['document_id']}/layout").json()["data"]
        created = client.post(f"/api/v1/certificate-format-versions/{cloned['id']}/tests", json={
            **ACTOR, "expected_revision": cloned["revision"], "layout_id": prepared["id"]}).json()["data"]
        assert runner.run_once()
        assert client.post(f"/api/v1/certificate-format-tests/{created['id']}/confirm", json=ACTOR).status_code == 200
    activated = client.post(f"/api/v1/certificate-format-versions/{cloned['id']}/activate", json={**ACTOR, "expected_revision": 1})
    assert activated.status_code == 200, activated.text
    assert len(activated.json()["data"]["lifecycle"][-1]["validation"]) == 3
    assert client.get(f"/api/v1/certificate-format-versions/{version['id']}").json()["data"]["status"] == "retired"
    with client.app.state.sessions() as session:
        assert len(template_snapshots(session)) == 1
    monkeypatch.setattr("backend.app.application.format_activation.extractor_hash", lambda: "changed")
    with client.app.state.sessions() as session:
        assert template_snapshots(session) == []
        from backend.app.domain.errors import ConflictError
        import pytest
        with pytest.raises(ConflictError):
            template_snapshots(session, cloned["id"])
