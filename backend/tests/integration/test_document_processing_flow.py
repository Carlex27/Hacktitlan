from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
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


def test_upload_worker_and_persistence_complete_flow(processing_settings: Settings):
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
        duplicate_response = client.post(
            "/api/v1/documents",
            files={"file": ("renamed.pdf", b"%PDF-1.7\nfixture", "application/pdf")},
        )

    assert job["status"] == "succeeded"
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
