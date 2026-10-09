import json
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from backend.app.api.app import create_app
from backend.app.application.certificate_extraction import CertificateExtractionService
from backend.app.application.worker import Worker
from backend.app.certificate_parser.adapters import AdapterRegistry
from backend.app.certificate_parser.generic_extractor import GenericExtractionResult
from backend.app.infrastructure.database.session import create_session_factory
from backend.app.infrastructure.files import FileStorage
from backend.tests.integration.test_document_processing_flow import processing_settings, upload  # noqa: F401
from backend.tests.unit.test_ollama_verification import client as assistant_client, document


def test_worker_persists_field_verification_and_api_accepts_saved_proposal(processing_settings):
    normalized = CertificateExtractionService.normalize_known_payload({"rows": [{
        "product_id": "A", "heat_no": "H1", "width_mm": 900, "thickness_mm": 1,
        "chemistry": {"C": "13"}, "chemistry_scales": {"C": -2}}]})
    reader = MagicMock()
    reader.read.return_value = document()
    generic = MagicMock()
    generic.extract.return_value = GenericExtractionResult(True, normalized, [], [], [])
    assistant = assistant_client([])

    def respond(request, **_kwargs):
        data = json.loads(json.loads(request.data)["messages"][1]["content"])
        comparisons = [{"field_id": f["field_id"], "status": "not_verifiable",
                        "raw_value": None, "source_id": None, "header_id": None} for f in data["fields"]]
        for comparison in comparisons:
            if comparison["field_id"] == "p0.composition_pct.C":
                comparison.update(status="discrepancy", raw_value="13", source_id="t0r1c1", header_id="t0r0c1")
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps({"done": True,
            "message": {"content": json.dumps({"fields": comparisons})}}).encode()
        return response

    assistant.opener.open.side_effect = respond
    extractor = CertificateExtractionService(reader, AdapterRegistry(), generic, assistant)
    with TestClient(create_app(processing_settings)) as api:
        created = upload(api, b"%PDF-1.7\nfield-verification")
        assert Worker(processing_settings, create_session_factory(processing_settings),
            FileStorage(processing_settings.storage_root, processing_settings.max_pdf_bytes), extractor).run_once()
        path = f"/api/v1/certificates/{created['certificate_id']}"
        certificate = api.get(path).json()["data"]
        carbon = next(o for o in certificate["observations"] if o["field_path"] == "composition_pct.C")
        assert carbon["normalized_value"] == .13
        assert carbon["verification"]["normalized_value"] == .0013
        assert carbon["verification"]["header_text"] == "C 10^-4"
        assert certificate["approval_status"] == "needs_review"
        correction = api.post(f"/api/v1/observations/{carbon['id']}/corrections", json={
            "accept_verification": True, "normalized_value": 99, "raw_value": "invented",
            "person_name": "Ana", "reason": "Revisé la escala en el PDF"})
        assert correction.status_code == 200
        updated = api.get(path).json()["data"]
        current = next(o for o in updated["observations"] if o["field_path"] == "composition_pct.C" and o["is_current"])
        assert current["raw_value"] == "13" and current["normalized_value"] == .0013
        assert current["supersedes_id"] == carbon["id"]
        assert current["page_number"] == 1 and "C 10^-4" in current["source_text"]
        assert float(updated["chemical_compositions"][0]["percentage"]) == .0013
        assert next(o for o in updated["observations"] if o["id"] == carbon["id"])["normalized_value"] == .13
        assert api.post(f"/api/v1/observations/{carbon['id']}/corrections", json={
            "accept_verification": True, "person_name": "Ana", "reason": "Repetido"}).status_code == 409


def test_molino3_conflicting_ocr_proposal_can_be_accepted_with_audit(processing_settings):
    from backend.tests.unit.test_real_mill_ocr_layouts import read_snapshot
    reader = MagicMock()
    reader.read.return_value = read_snapshot(3)
    extractor = CertificateExtractionService(reader)
    with TestClient(create_app(processing_settings)) as api:
        created = upload(api, b"%PDF-1.7\nreal-ocr-carbon")
        assert Worker(processing_settings, create_session_factory(processing_settings),
            FileStorage(processing_settings.storage_root, processing_settings.max_pdf_bytes), extractor).run_once()
        path = f"/api/v1/certificates/{created['certificate_id']}"
        certificate = api.get(path).json()["data"]
        carbon = next(o for o in certificate["observations"] if o["field_path"] == "composition_pct.C" and o["raw_value"] == "39")
        assert carbon["normalized_value"] == .39
        assert carbon["verification"]["normalized_value"] == .33
        assert carbon["verification"]["source_text"] == "33"
        correction = api.post(f"/api/v1/observations/{carbon['id']}/corrections", json={
            "accept_verification": True, "person_name": "Ana", "reason": "Verifiqué 33 en el PDF original"})
        assert correction.status_code == 200
        updated = api.get(path).json()["data"]
        replacement = next(o for o in updated["observations"] if o["supersedes_id"] == carbon["id"])
        assert replacement["raw_value"] == "33" and replacement["normalized_value"] == .33
        assert replacement["page_number"] == 1
        assert next(o for o in updated["observations"] if o["id"] == carbon["id"])["normalized_value"] == .39
