"""Prepare and preview documents in background without persisting certificate data."""
from datetime import datetime, timezone
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

from pydantic import TypeAdapter
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from backend.app.application.certificate_extraction import DocumentReader
from backend.app.config import Settings
from backend.app.certificate_parser.templates import TemplateConfiguration, extractor_hash, preview_template
from backend.app.domain.document import DocumentLayout, PageSource
from backend.app.infrastructure.database.models import (
    CertificateFormatTest, Document, Job, PreparedDocumentLayout, StoredFile,
)
from backend.app.infrastructure.files import FileStorage
from backend.app.infrastructure.ocr import OcrCancellationRequested

LAYOUT_ADAPTER = TypeAdapter(DocumentLayout)


def execute_format_job(job_id: int, sessions: sessionmaker[Session], storage: FileStorage,
                       reader: DocumentReader, settings: Settings) -> None:
    def cancelled() -> bool:
        with sessions() as session:
            job = session.get(Job, job_id)
            return job is None or job.status == "cancelled"

    def progress(current: int, total: int) -> None:
        with sessions.begin() as session:
            job = session.get(Job, job_id)
            if job is not None and job.status == "running" and total > 0:
                job.progress = max(job.progress, min(95, 10 + int(80 * current / total)))

    with sessions() as session:
        job = session.get(Job, job_id)
        if job is None or job.document_id is None:
            raise ValueError("Trabajo sin documento")
        kind, document_id, payload = job.kind, job.document_id, job.payload_json
        document = session.get(Document, document_id)
        stored = session.get(StoredFile, document.stored_file_id) if document else None
        if stored is None:
            raise ValueError("Archivo de preparación no disponible")
        document_hash = stored.sha256
        original_name = stored.original_name
        path = storage.resolve(stored.relative_path)
        if sha256(path.read_bytes()).hexdigest() != document_hash:
            raise ValueError("El archivo no coincide con su hash registrado")
        if kind == "test_certificate_format":
            test = session.get(CertificateFormatTest, payload["test_id"])
            layout = session.get(PreparedDocumentLayout, test.layout_id) if test else None
            if test is None or layout is None or test.document_id != document_id:
                raise ValueError("La prueba o su layout ya no están disponibles")
            if test.extractor_sha256 != extractor_hash() or layout.document_sha256 != document_hash:
                raise ValueError("El extractor o archivo cambió desde que se solicitó la prueba")
            configuration = TemplateConfiguration.model_validate(test.configuration_json)
            if configuration.sha256 != test.configuration_sha256:
                raise ValueError("Configuración de prueba incompatible con su hash")
            prepared = LAYOUT_ADAPTER.validate_python(layout.layout_json)
    if cancelled():
        return
    progress(0, 1)
    if kind == "prepare_layout":
        if payload["document_sha256"] != document_hash:
            raise ValueError("El archivo cambió desde que se solicitó la preparación")
        try:
            prepared = reader.read(path, page_callback=progress, cancel_check=cancelled)
        except OcrCancellationRequested:
            if cancelled():
                return
            raise
        finally:
            release = getattr(reader, "release", None)
            if callable(release):
                release()
        if prepared.sha256 != document_hash:
            raise ValueError("El lector devolvió un documento distinto")
        app_root = Path(__file__).parents[1]
        reader_files = (app_root / "document_ingestion/pdf_reader.py", app_root / "infrastructure/ocr/reader.py",
                        app_root / "infrastructure/ocr/geometry.py")
        prepared = replace(prepared, file_name=original_name, metadata={**prepared.metadata, "layout_preparation": {
            "schema_version": 1, "reader": type(reader).__name__,
            "source_sha256": sha256(b"".join(p.read_bytes() for p in reader_files)).hexdigest(),
            "ocr_enabled": settings.ocr_enabled, "ocr_language": settings.ocr_language,
            "ocr_min_confidence": settings.ocr_min_confidence,
        }})
        result = None
    else:
        result = preview_template(prepared, configuration)
    with sessions.begin() as session:
        job = session.scalar(select(Job).where(Job.id == job_id).with_for_update())
        if job is None or job.status != "running":
            return
        if kind == "prepare_layout":
            layout = PreparedDocumentLayout(document_id=document_id, job_id=job_id,
                document_sha256=document_hash, layout_json=LAYOUT_ADAPTER.dump_python(prepared, mode="json"))
            session.add(layout)
            session.flush()
            job.result_json = {"layout_id": layout.id}
            job.status = "needs_ocr" if any(p.source is PageSource.UNREADABLE for p in prepared.pages) else "succeeded"
        else:
            test = session.get(CertificateFormatTest, payload["test_id"])
            if test is None:
                raise ValueError("La prueba fue eliminada")
            test.result_json = result.model_dump(mode="json")
            job.result_json = {"test_id": test.id, "status": result.status}
            job.status = "succeeded" if result.status == "success" else (
                "needs_ocr" if result.status == "needs_ocr" else "needs_review")
        job.progress = 100
        job.error_code = None
        job.error_message = None
        job.finished_at = datetime.now(timezone.utc)
        job.heartbeat_at = job.finished_at
