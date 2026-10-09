from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
from typing import Any

import pytest
from openpyxl import Workbook
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from backend.app.api.app import create_app
from backend.app.application.certificate_extraction import CertificateExtractionService
from backend.app.application.worker import Worker
from backend.app.config import Settings
from backend.app.infrastructure.database.session import create_session_factory
from backend.app.infrastructure.files import FileStorage


FIXTURE = Path(__file__).parents[3] / "data" / "samples" / "molino-1.raw.json"


class StaticExtractor:
    def __init__(self, result: dict[str, Any]) -> None:
        self.result = result

    def analyze_pdf(self, _path: str | Path) -> dict[str, Any]:
        return self.result


@pytest.mark.parametrize("provisional_zinc", [False, True])
def test_unknown_rolling_candidates_persist_and_operator_selection_is_audited(processing_settings, provisional_zinc):
    from sqlalchemy import select
    from backend.app.application.classification_service import ClassificationService
    from backend.app.infrastructure.database.models import Product
    from backend.tests.unit.test_classification_engine import complete_non_alloy_chemistry

    normalized = CertificateExtractionService.normalize_known_payload(json.loads(FIXTURE.read_text(encoding="utf-8")))
    product = normalized["products"][0]
    product.update(rolling=None, thickness_mm=1.71, width_mm=1220,
                   condition=["not_pickled"], composition_pct={
                       key: float(value) for key, value in complete_non_alloy_chemistry().items()
                   },
                   mechanical_properties={"yield_strength_mpa": 230})
    normalized["products"] = [product]
    if provisional_zinc:
        product["composition_pct"] = {"C": .0136, "Mn": .116}
        product["coating"] = {"metal": "Zn", "process": "electrolytic",
                              "superior_g_m2": 19.1, "inferior_g_m2": 19.1}
    extraction = {"status": "needs_review", "certificate": normalized,
                  "document": {"page_count": 1}, "adapter": "test_complete_except_rolling"}
    sessions = create_session_factory(processing_settings)
    storage = FileStorage(processing_settings.storage_root, processing_settings.max_pdf_bytes)
    with TestClient(create_app(processing_settings)) as client:
        created = upload(client)
        assert Worker(processing_settings, sessions, storage, extractor=StaticExtractor(extraction)).run_once()
        with sessions.begin() as session:
            row = session.scalar(select(Product).where(Product.certificate_id == created["certificate_id"]))
            row.properties_json = {**row.properties_json, "coated": provisional_zinc, "pattern_in_relief": False}
            session.flush()
            run_id = ClassificationService(processing_settings).classify_certificate(
                session, certificate_id=created["certificate_id"], person_name="Test operator",
                reason="Only rolling is unknown",
            ).id
        run = client.get(f"/api/v1/classification-runs/{run_id}").json()["data"]
        result = run["results"][0]
        assert result["outcome"] == "needs_review" and result["fraction"] is None
        assert len(result["candidates"]) == 2
        for candidate in result["candidates"]:
            assert "rolling" in candidate["details"]["missing_fields"]
            if provisional_zinc:
                assert "composition_pct.Cr" in candidate["details"]["missing_fields"]
            else:
                assert candidate["details"]["missing_fields"] == ["rolling"]
            assert candidate["factors"][-1]["observed"] == {"rolling": None}
            assert candidate["factors"][-1]["outcome"] == "unknown"
        response = client.post(f"/api/v1/classification-results/{result['id']}/select", json={
            "candidate_id": result["candidates"][0]["id"], "person_name": "Test operator",
            "reason": "Confirmed cold rolling against additional evidence",
        })
        assert response.status_code == 200
        detail = client.get(f"/api/v1/certificates/{created['certificate_id']}").json()["data"]
        assert detail["products"][0]["rolling"] is None


@pytest.fixture()
def processing_settings(tmp_path) -> Settings:
    base = Settings()
    database_url = base.test_database_url
    if not database_url:
        pytest.skip("Requires the explicit hacktitlan_test PostgreSQL database")
    assert database_url.rsplit("/", 1)[-1].split("?", 1)[0] == "hacktitlan_test"

    engine = create_engine(database_url)
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "TRUNCATE extraction_runs, jobs, observations, chemical_compositions, "
                    "products, heats, mill_certificates, documents, stored_files, manufacturers "
                    "RESTART IDENTITY CASCADE"
                )
            )
    finally:
        engine.dispose()

    return Settings(
        database_url=database_url,
        test_database_url=database_url,
        storage_root=tmp_path / "storage",
        backup_root=tmp_path / "backups",
    )


def upload(client: TestClient, content: bytes = b"%PDF-1.7\nfixture") -> dict[str, Any]:
    response = client.post(
        "/api/v1/documents",
        files={"file": ("certificate.pdf", content, "application/pdf")},
    )
    assert response.status_code == 202
    return response.json()["data"]


def test_calvert_ocr_worker_persists_one_coil_with_supplemental_evidence(processing_settings):
    from backend.tests.unit.test_calvert_adapter import layout

    class Reader:
        def read(self, *_args, **_kwargs):
            return layout()

    extraction = CertificateExtractionService(Reader()).analyze_pdf("calvert.pdf")
    sessions = create_session_factory(processing_settings)
    storage = FileStorage(processing_settings.storage_root, processing_settings.max_pdf_bytes)
    with TestClient(create_app(processing_settings)) as client:
        created = upload(client)
        assert Worker(processing_settings, sessions, storage, extractor=StaticExtractor(extraction)).run_once()
        response = client.get(f"/api/v1/certificates/{created['certificate_id']}")
        assert response.status_code == 200
        certificate = response.json()["data"]
        assert certificate["certificate_no"] == "2302380630"
        assert certificate["standard"] == "M2021 SP221PE"
        assert certificate["certificate_date"] == "2026-06-28"
        assert len(certificate["products"]) == 1
        assert certificate["products"][0]["product_identifier"] == "2302380630"
        assert float(certificate["products"][0]["weight_kg"]) == 10000
        assert certificate["heats"][0]["heat_no"] == "2620689"
        assert len(certificate["chemical_compositions"]) == 17
        assert any(observation["page_number"] == 4 and "A1011 CS-B" in str(observation["raw_value"])
                   for observation in certificate["observations"])


@pytest.mark.parametrize("support_document", [False, True])
def test_xlsx_upload_real_worker_provenance_and_download(processing_settings: Settings, support_document):
    workbook = Workbook()
    sheet = workbook.active
    if support_document:
        sheet.append(["SPEC", "Alloy or Non-Alloy", "Yield Point(N/mm2)"])
        sheet.append(["SPCC", "non-alloy", "<355"])
    else:
        sheet.append(["MILL NO", "PRODUCTION NAME", "WIDTH", "THICK", "C", "Ti", "CAST NO"])
        sheet.append(["CERT-1", "HOT ROLLED STEEL SHEET IN COIL", 1000, 2, .05, .05, "G82765"])
        sheet.append(["CERT-2", "HOT ROLLED STEEL SHEET IN COIL", 1000, 2, .05, .05, "G82765"])
    output = BytesIO()
    workbook.save(output)
    content = output.getvalue()
    sessions = create_session_factory(processing_settings)
    storage = FileStorage(processing_settings.storage_root, processing_settings.max_pdf_bytes)
    with TestClient(create_app(processing_settings)) as client:
        response = client.post("/api/v1/documents", files={"file": ("mill.xlsx", content)})
        assert response.status_code == 202
        created = response.json()["data"]
        assert Worker(processing_settings, sessions, storage).run_once()
        job = client.get(f"/api/v1/jobs/{created['job_id']}").json()["data"]
        assert job["status"] == "needs_review", job
        certificate = client.get(f"/api/v1/certificates/{created['certificate_id']}").json()["data"]
        assert certificate["source_file_name"] == "mill.xlsx"
        reviews = client.get("/api/v1/document-reviews").json()["data"]
        assert next(item for item in reviews if item["certificate_id"] == created["certificate_id"])["source_file_name"] == "mill.xlsx"
        history = client.get("/api/v1/certificates").json()["data"]
        assert next(item for item in history if item["id"] == created["certificate_id"])["source_file_name"] == "mill.xlsx"
        assert certificate["approval_status"] == "needs_review"
        detail = client.get(f"/api/v1/documents/{created['document_id']}/spreadsheet").json()["data"]
        assert detail["sheets"][0]["rows"][1]["cells"]["A2"] == ("SPCC" if support_document else "CERT-1")
        assert detail["formula_policy"] == "preserved_not_evaluated"
        downloaded = client.get(detail["file_url"])
        assert downloaded.content == content
        assert "spreadsheetml.sheet" in downloaded.headers["content-type"]
        assert client.post("/api/v1/documents", files={"file": ("renamed.xlsx", content)}).status_code == 200
        if support_document:
            assert certificate["products"] == []
            assert detail["specification_records"][0]["yield_strength"]["normalized_value"]["operator"] == "<"
        else:
            assert len(certificate["products"]) == 2
            assert [heat["heat_no"] for heat in certificate["heats"]] == ["G82765"]
            chemistry = certificate["chemical_compositions"]
            assert len(chemistry) == 4
            assert all(item["product_id"] is not None for item in chemistry)
            source_cells = {item["source_text"] for item in certificate["observations"] if item["field_path"] == "composition_pct.Ti"}
            assert source_cells == {"'Sheet'!F2: 0.05", "'Sheet'!F3: 0.05"}
        spec = client.get("/openapi.json").json()
        assert "/api/v1/documents/{document_id}/spreadsheet" in spec["paths"]
        assert "DocumentUploadEnvelope" in spec["components"]["schemas"]


@pytest.mark.parametrize("classification_fails", [False, True])
def test_upload_worker_and_persistence_complete_flow(processing_settings: Settings, monkeypatch, classification_fails):
    if classification_fails:
        def unavailable(*args, **kwargs):
            raise RuntimeError("Catálogo no disponible")
        monkeypatch.setattr("backend.app.application.worker.ClassificationService.classify_certificate", unavailable)
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    normalized = CertificateExtractionService.normalize_known_payload(raw)
    extraction = {
        "status": "extracted",
        "document": {"file_name": "certificate.pdf", "sha256": "fixture", "page_count": 1},
        "detection": {"kind": "mill_certificate", "confidence": 1.0, "signals": []},
        "field_candidates": [],
        "table_candidates": [],
        "adapter": "test-known-layout",
        "certificate": normalized,
    }
    sessions = create_session_factory(processing_settings)
    storage = FileStorage(processing_settings.storage_root, processing_settings.max_pdf_bytes)

    with TestClient(create_app(processing_settings)) as client:
        created = upload(client)
        queued = client.get(f"/api/v1/jobs/{created['job_id']}")
        assert queued.json()["data"]["status"] == "queued"

        assert Worker(
            processing_settings,
            sessions,
            storage,
            extractor=StaticExtractor(extraction),
        ).run_once()

        job = client.get(f"/api/v1/jobs/{created['job_id']}").json()["data"]
        certificate = client.get(
            f"/api/v1/certificates/{created['certificate_id']}"
        ).json()["data"]
        runs = client.get(f"/api/v1/certificates/{created['certificate_id']}/classification-runs").json()["data"]
        if classification_fails:
            assert runs == []
            assert job["result"]["classification_run_id"] is None
            assert job["error_code"] == "automatic_classification_failed"
            assert job["error_message"] == "Catálogo no disponible"
        else:
            assert len(runs) == 1
            classification = client.get(f"/api/v1/classification-runs/{runs[0]['id']}").json()["data"]
            assert job["result"]["classification_run_id"] == runs[0]["id"]
            assert {entry["product_id"] for entry in classification["results"]} == {entry["id"] for entry in certificate["products"]}
            assert all(1 <= len(entry["candidates"]) <= 3 for entry in classification["results"])
        duplicate_response = client.post(
            "/api/v1/documents",
            files={"file": ("renamed.pdf", b"%PDF-1.7\nfixture", "application/pdf")},
        )

    assert job["status"] == ("needs_review" if classification_fails else "succeeded")
    assert job["progress"] == 100
    assert job["result"]["adapter"] == "test-known-layout"
    assert certificate["certificate_no"] == "E02511200001"
    assert certificate["manufacturer"] == "BX Steel Posco Cold Rolled Sheet Co., Ltd."
    assert len(certificate["heats"]) == 1
    assert len(certificate["products"]) == 6
    assert len(certificate["chemical_compositions"]) == 7
    assert duplicate_response.status_code == 200
    assert duplicate_response.json()["data"] == {**created, "duplicate": True}


def test_incomplete_format_finishes_as_needs_review(processing_settings: Settings):
    extraction = {
        "status": "needs_review",
        "document": {"file_name": "unknown.pdf", "sha256": "fixture", "page_count": 2},
        "detection": {
            "kind": "possible_mill_certificate",
            "confidence": 0.55,
            "signals": ["product-identifiers"],
        },
        "field_candidates": [{"field": "heat_no", "raw_label": "Heat"}],
        "table_candidates": [],
    }
    sessions = create_session_factory(processing_settings)
    storage = FileStorage(processing_settings.storage_root, processing_settings.max_pdf_bytes)

    with TestClient(create_app(processing_settings)) as client:
        created = upload(client, b"%PDF-1.7\nunknown")
        assert Worker(
            processing_settings,
            sessions,
            storage,
            extractor=StaticExtractor(extraction),
        ).run_once()
        job = client.get(f"/api/v1/jobs/{created['job_id']}").json()["data"]
        certificate = client.get(
            f"/api/v1/certificates/{created['certificate_id']}"
        ).json()["data"]

    assert job["status"] == "needs_review"
    assert job["result"]["detection"]["confidence"] == 0.55
    assert certificate["products"] == []


def test_worker_persists_local_assistance_and_review_state(processing_settings):
    from unittest.mock import MagicMock
    from sqlalchemy import select
    from backend.app.certificate_parser.adapters import AdapterRegistry
    from backend.app.domain.document import BoundingBox, DocumentLayout, PageLayout, PageSource, TextBlock
    from backend.app.infrastructure.database.models import Document, ExtractionRun

    reader = MagicMock()
    reader.read.return_value = DocumentLayout("unknown.pdf", "hash", (
        PageLayout(1, 600, 800, 0, PageSource.DIGITAL, (
            TextBlock(1, "MILL TEST CERTIFICATE", BoundingBox(0, 0, 100, 20)),
        )),
    ))
    assistant = MagicMock()
    assistant.settings.ollama_model = "qwen3.5:4b"
    assistant.extract.return_value = CertificateExtractionService.normalize_known_payload(
        json.loads(FIXTURE.read_text(encoding="utf-8")))
    extractor = CertificateExtractionService(reader, AdapterRegistry(), ollama_extractor=assistant)
    sessions = create_session_factory(processing_settings)
    storage = FileStorage(processing_settings.storage_root, processing_settings.max_pdf_bytes)
    with TestClient(create_app(processing_settings)) as client:
        created = upload(client, b"%PDF-1.7\nollama-proposal")
        assert Worker(processing_settings, sessions, storage, extractor=extractor).run_once()
        job = client.get(f"/api/v1/jobs/{created['job_id']}").json()["data"]
        certificate = client.get(f"/api/v1/certificates/{created['certificate_id']}").json()["data"]
    assert job["status"] == "needs_review"
    assert job["result"]["adapter"] == "ollama_local"
    assert certificate["products"]
    with sessions() as session:
        document = session.get(Document, created["document_id"])
        run = session.scalar(select(ExtractionRun).where(ExtractionRun.document_id == document.id))
        assert document.metadata_json["llm_assistance"]["model"] == "qwen3.5:4b"
        assert run.detection_json["llm_assistance"]["status"] == "needs_review"
        assert run.normalized_json == assistant.extract.return_value


@pytest.mark.parametrize("has_issue_date", [True, False])
def test_generic_metadata_persists_description_and_never_uses_delivery_as_issue(processing_settings, has_issue_date):
    from sqlalchemy import select
    from backend.tests.unit.test_real_mill_ocr_layouts import read_snapshot
    from backend.app.certificate_parser.generic_extractor import GenericCertificateExtractor
    from backend.app.infrastructure.database.models import ExtractionRun

    normalized = GenericCertificateExtractor().extract(read_snapshot(3)).certificate
    normalized["document"]["delivery_date_raw"] = "2026-06-30"
    if not has_issue_date:
        normalized["document"]["issue_date_raw"] = None
    extraction = {"status": "needs_review", "adapter": "generic_layout_extractor", "certificate": normalized,
                  "document": {"file_name": "molino-3.pdf", "sha256": "fixture", "page_count": 1}}
    sessions = create_session_factory(processing_settings)
    storage = FileStorage(processing_settings.storage_root, processing_settings.max_pdf_bytes)
    with TestClient(create_app(processing_settings)) as client:
        created = upload(client, b"%PDF-1.7\nmetadata")
        assert Worker(processing_settings, sessions, storage, extractor=StaticExtractor(extraction)).run_once()
        certificate = client.get(f"/api/v1/certificates/{created['certificate_id']}").json()["data"]
    assert certificate["certificate_date"] == ("2026-06-12" if has_issue_date else None)
    assert certificate["product_name"] == "HOT ROLLED SHEET-COIL (MILL EDGE)"
    assert certificate["manufacturer"] == "CHINA STEEL CORPORATION"
    assert len(certificate["products"]) == 11
    with sessions() as session:
        run = session.scalar(select(ExtractionRun).where(ExtractionRun.document_id == created["document_id"]))
        assert "ABOUT" in run.normalized_json["document"]["shipping_date_raw"]
        assert run.normalized_json["document"]["field_evidence"]["product_name"]


@pytest.mark.parametrize('snapshot,product_count,element_count', [('3-refined', 11, 12), ('4-refined', 6, 5)])
def test_real_mill_persists_two_heats_complete_chemistry_and_classification_candidates(processing_settings, snapshot, product_count, element_count):
    from backend.tests.unit.test_real_mill_ocr_layouts import read_snapshot

    class Reader:
        def read(self, _path, **_kwargs):
            return read_snapshot(snapshot)

    extraction = CertificateExtractionService(Reader()).analyze_pdf("snapshot.pdf")
    sessions = create_session_factory(processing_settings)
    storage = FileStorage(processing_settings.storage_root, processing_settings.max_pdf_bytes)
    with TestClient(create_app(processing_settings)) as client:
        created = upload(client)
        assert Worker(processing_settings, sessions, storage, extractor=StaticExtractor(extraction)).run_once()
        certificate = client.get(f"/api/v1/certificates/{created['certificate_id']}").json()["data"]
        assert {heat["heat_no"] for heat in certificate["heats"]} == (
            {"3VL99", "1FN43"} if snapshot == '3-refined' else {"SB06562", "SB05270"})
        if snapshot == '3-refined':
            assert all(heat["grade"] == "1035" and heat["standard"] == "SAE 1035" for heat in certificate["heats"])
        else:
            assert all(heat["standard"] == "SECC" for heat in certificate["heats"])
        assert len(certificate["products"]) == product_count
        for product in certificate["products"]:
            chemistry = {item["element"]: item["percentage"] for item in certificate["chemical_compositions"]
                         if item["product_id"] == product["id"] or
                         (item["product_id"] is None and item["heat_id"] == product["heat_id"])}
            assert len(chemistry) == element_count
            if snapshot == '3-refined':
                assert float(chemistry['C']) == (.35 if product['product_identifier'] in {'14159481', '14159482'} else .33)
            else:
                assert certificate['product_name'] == 'EG COIL(ZN)'
                assert float(chemistry['S']) == (.0061 if product['product_identifier'].startswith('CBG2629') else .0054)
        runs = client.get(f"/api/v1/certificates/{created['certificate_id']}/classification-runs").json()["data"]
        classification = client.get(f"/api/v1/classification-runs/{runs[0]['id']}").json()["data"]
        assert len(classification["results"]) == product_count
        if snapshot == '3-refined':
            assert all(len(result["candidates"]) == 3 for result in classification["results"])
