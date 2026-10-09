"""Background job processor using PostgreSQL as the queue."""

from __future__ import annotations

from datetime import datetime, timezone
from contextlib import contextmanager
import logging
from pathlib import Path
import socket
import tempfile
from threading import Event, Thread
import time
from typing import Any, Protocol
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.orm import Session, sessionmaker

from backend.app.application.certificate_extraction import CertificateExtractionService
from backend.app.application.persistence import CertificatePersistenceService
from backend.app.application.classification_service import ClassificationService
from backend.app.config import Settings, get_settings
from backend.app.document_ingestion.factory import build_document_reader
from backend.app.domain.enums import JobKind, ProcessingStatus
from backend.app.infrastructure.database.job_repository import JobRepository
from backend.app.infrastructure.database.models import (
    ClassificationResult,
    Document,
    Export,
    ExtractionRun,
    Job,
    MillCertificate,
    StoredFile,
)
from backend.app.infrastructure.database.session import create_session_factory
from backend.app.infrastructure.files import FileStorage
from backend.app.infrastructure.logging import configure_logging
from backend.app.infrastructure.ollama import OllamaExtractor
from backend.app.reporting.excel_export import ExcelExportService

logger = logging.getLogger(__name__)


class DocumentExtractor(Protocol):
    def analyze_pdf(self, path: str | Path) -> dict[str, Any]: ...


class Worker:
    def __init__(
        self,
        settings: Settings,
        sessions: sessionmaker[Session],
        storage: FileStorage,
        extractor: DocumentExtractor | None = None,
    ) -> None:
        self.settings = settings
        self.sessions = sessions
        self.storage = storage
        self.repository = JobRepository()
        self.worker_id = f"{socket.gethostname()}-{uuid4().hex[:8]}"
        self.extractor = extractor or CertificateExtractionService(
            build_document_reader(settings),
            ollama_extractor=OllamaExtractor(settings) if settings.ollama_enabled else None,
        )
        self.persistence = CertificatePersistenceService(settings)

    def run_once(self) -> bool:
        with self.sessions.begin() as session:
            self.repository.recover_stale(session, self.settings.worker_stale_after_seconds)
            job = self.repository.claim_next(session, self.worker_id)
            if (
                job is not None
                and job.kind == JobKind.EXTRACT_DOCUMENT.value
                and job.document_id is not None
            ):
                document = session.get(Document, job.document_id)
                if document is not None:
                    document.processing_status = ProcessingStatus.RUNNING.value
            job_id = job.id if job else None
        if job_id is None:
            return False
        try:
            self._execute(job_id)
        except Exception as exc:  # worker boundary must persist failures
            logger.exception("job_failed", extra={"job_id": job_id})
            with self.sessions.begin() as session:
                job = session.get(Job, job_id)
                if job is not None:
                    job.status = (
                        ProcessingStatus.QUEUED.value
                        if job.attempts < job.max_attempts
                        else ProcessingStatus.FAILED.value
                    )
                    job.error_code = type(exc).__name__
                    job.error_message = str(exc)[:4000]
                    job.finished_at = (
                        datetime.now(timezone.utc)
                        if job.status == ProcessingStatus.FAILED.value
                        else None
                    )
                    if job.status == ProcessingStatus.QUEUED.value:
                        job.progress = 0
                        job.worker_id = None
                        job.heartbeat_at = None
                    if job.kind == JobKind.EXTRACT_DOCUMENT.value and job.document_id is not None:
                        document = session.get(Document, job.document_id)
                        if document is not None:
                            document.processing_status = job.status
                    export_id = job.payload_json.get("export_id")
                    export = session.get(Export, export_id) if export_id else None
                    if export is not None:
                        export.status = "queued" if job.status == ProcessingStatus.QUEUED.value else "failed"
                        export.error_message = job.error_message
        return True

    def _execute(self, job_id: int) -> None:
        with self.sessions() as session:
            job = session.get(Job, job_id)
            if job is None:
                raise ValueError("El trabajo no existe")
            kind = job.kind
        if kind == JobKind.EXTRACT_DOCUMENT.value:
            self._execute_extraction(job_id)
        elif kind == JobKind.EXPORT_XLSX.value:
            self._execute_export(job_id)
        elif kind == JobKind.RECLASSIFY.value:
            self._execute_reclassification(job_id)
        else:
            raise ValueError("Tipo de trabajo no soportado por este worker")

    def _execute_extraction(self, job_id: int) -> None:
        with self.sessions() as session:
            job = session.get(Job, job_id)
            if job is None or job.document_id is None:
                raise ValueError("Tipo de trabajo no soportado por este worker")
            document = session.get(Document, job.document_id)
            stored_file = session.get(StoredFile, document.stored_file_id) if document else None
            if document is None or stored_file is None:
                raise ValueError("El documento o archivo del trabajo no existe")
            path = self.storage.resolve(stored_file.relative_path)
            document_id = document.id

        def page_progress(current_page: int, total_pages: int) -> None:
            if total_pages <= 0:
                return
            progress_pct = min(95, max(5, int((current_page / total_pages) * 80) + 10))
            with self.sessions.begin() as s:
                j = s.get(Job, job_id)
                if j and j.status == "running":
                    j.progress = max(j.progress, progress_pct)

        def is_cancelled() -> bool:
            with self.sessions() as s:
                j = s.get(Job, job_id)
                return bool(j and j.status == "cancelled")

        page_progress(0, 1)
        with self._heartbeat(job_id):
            try:
                analyze = getattr(self.extractor, "analyze_document", self.extractor.analyze_pdf)
                try:
                    result = analyze(
                        path, page_callback=page_progress, cancel_check=is_cancelled
                    )
                except TypeError:
                    result = analyze(path)
            except Exception as exc:
                if exc.__class__.__name__ == "OcrCancellationRequested":
                    logger.info("job_cancelled_during_ocr", extra={"job_id": job_id})
                    return
                raise
            finally:
                release = getattr(self.extractor, "release", None)
                if callable(release):
                    release()
        status_map = {
            "extracted": ProcessingStatus.SUCCEEDED,
            "needs_review": ProcessingStatus.NEEDS_REVIEW,
            "needs_ocr": ProcessingStatus.NEEDS_OCR,
            "unsupported": ProcessingStatus.NEEDS_REVIEW,
        }
        final_status = status_map[result["status"]]
        with self.sessions.begin() as session:
            job = session.get(Job, job_id)
            if job is not None and job.status == ProcessingStatus.RUNNING.value:
                job.progress = 95
        with self.sessions.begin() as session:
            job = session.get(Job, job_id)
            document = session.get(Document, document_id)
            if job is None or document is None:
                raise ValueError("El trabajo fue eliminado durante el procesamiento")
            classification_run_id = None
            if result.get("certificate") is not None:
                certificate = self.persistence.persist_normalized(
                    session,
                    document_id=document_id,
                    normalized=result["certificate"],
                )
                if final_status == ProcessingStatus.NEEDS_REVIEW:
                    certificate.approval_status = "needs_review"
                if result["certificate"].get("products"):
                    try:
                        with session.begin_nested():
                            run = ClassificationService(self.settings).classify_certificate(
                                session,
                                certificate_id=certificate.id,
                                person_name=self.worker_id,
                                reason="Sugerencias automáticas tras extraer el acta",
                            )
                            session.flush()
                            classification_run_id = run.id
                    except Exception as exc:
                        # Conservar la extracción aunque el catálogo o la clasificación fallen.
                        logger.exception("automatic_classification_failed", extra={"job_id": job_id})
                        final_status = ProcessingStatus.NEEDS_REVIEW
                        certificate.approval_status = "needs_review"
                        job.error_code = "automatic_classification_failed"
                        job.error_message = str(exc)[:4000]
            document.processing_status = final_status.value
            document.page_count = result["document"].get("page_count")
            document.metadata_json = {
                **(document.metadata_json or {}),
                "detection": result.get("detection"),
                "adapter": result.get("adapter"),
                "ingestion": result["document"].get("ingestion") or {},
                "extraction_reasons": result.get("reasons") or [],
                "llm_assistance": result.get("llm_assistance"),
            }
            job.status = final_status.value
            job.progress = 100
            job.finished_at = datetime.now(timezone.utc)
            job.heartbeat_at = job.finished_at
            job.result_json = {
                "classification_run_id": classification_run_id,
                "status": result["status"],
                "adapter": result.get("adapter"),
                "detection": result.get("detection"),
            }
            session.add(
                ExtractionRun(
                    document_id=document_id,
                    job_id=job_id,
                    status=final_status.value,
                    adapter_name=result.get("adapter"),
                    detection_json={
                        "detection": result.get("detection") or {},
                        "field_candidates": result.get("field_candidates") or [],
                        "table_candidates": result.get("table_candidates") or [],
                        "unmapped_blocks": result.get("unmapped_blocks") or [],
                        "llm_assistance": result.get("llm_assistance"),
                    },
                    normalized_json=result.get("certificate"),
                    warnings_json=result.get("reasons") or [],
                )
            )

    def _execute_export(self, job_id: int) -> None:
        with self.sessions() as session:
            job = session.get(Job, job_id)
            export_id = job.payload_json.get("export_id") if job else None
            export = session.get(Export, export_id) if export_id else None
            if job is None or export is None:
                raise ValueError("La solicitud de exportación no existe")
            export.status = "running"
            session.commit()
            certificate_ids = list(export.scope_json.get("certificate_ids") or [])
            heat_ids = list(export.scope_json.get("heat_ids") or [])
            classification_run_ids = list(
                export.scope_json.get("classification_run_ids") or []
            )
            official = bool(export.scope_json.get("official"))
            suggested_name = f"clasificacion_{datetime.now(timezone.utc):%Y-%m-%d}_export-{export.id}.xlsx"
            with tempfile.NamedTemporaryFile(
                suffix=".xlsx", dir=self.storage.temp_root, delete=False
            ) as temporary:
                temporary_path = temporary.name
            try:
                with self._heartbeat(job_id):
                    ExcelExportService(self.settings).export_certificates(
                        session,
                        certificate_ids=certificate_ids,
                        heat_ids=heat_ids or None,
                        classification_run_ids=classification_run_ids if "classification_run_ids" in export.scope_json else None,
                        destination=Path(temporary_path),
                        official=official,
                    )
                artifact = self.storage.store_generated(
                    Path(temporary_path),
                    suggested_name,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            finally:
                Path(temporary_path).unlink(missing_ok=True)

        with self.sessions.begin() as session:
            job = session.get(Job, job_id)
            export = session.get(Export, export_id)
            if job is None or export is None:
                raise ValueError("La exportación fue eliminada durante el procesamiento")
            stored = session.scalar(select(StoredFile).where(StoredFile.sha256 == artifact.sha256))
            if stored is None:
                stored = StoredFile(
                    sha256=artifact.sha256,
                    original_name=artifact.original_name,
                    storage_name=artifact.storage_name,
                    relative_path=artifact.relative_path,
                    media_type=artifact.media_type,
                    size_bytes=artifact.size_bytes,
                    status="ready",
                )
                session.add(stored)
                session.flush()
            export.stored_file_id = stored.id
            export.sha256 = artifact.sha256
            export.status = "succeeded"
            export.error_message = None
            job.status = ProcessingStatus.SUCCEEDED.value
            job.progress = 100
            job.finished_at = datetime.now(timezone.utc)
            job.heartbeat_at = job.finished_at
            job.result_json = {"export_id": export.id, "sha256": artifact.sha256}

    def _execute_reclassification(self, job_id: int) -> None:
        with self._heartbeat(job_id):
            with self.sessions.begin() as session:
                job = session.get(Job, job_id)
                if job is None or job.document_id is None:
                    raise ValueError("El trabajo de reclasificación no existe")
                payload = job.payload_json
                run = ClassificationService(self.settings).classify_certificate(
                    session,
                    certificate_id=int(payload["certificate_id"]),
                    person_name=str(payload["person_name"]),
                    reason=str(payload["reason"]),
                    rule_set_id=payload.get("rule_set_id"),
                    source_run_id=payload.get("source_run_id"),
                )
                session.flush()
                outcomes = session.scalars(
                    select(ClassificationResult.outcome).where(
                        ClassificationResult.classification_run_id == run.id
                    )
                ).all()
                complete = bool(outcomes) and all(value == "classified" for value in outcomes)
                job.status = (
                    ProcessingStatus.SUCCEEDED.value
                    if complete else ProcessingStatus.NEEDS_REVIEW.value
                )
                job.progress = 100
                job.finished_at = datetime.now(timezone.utc)
                job.heartbeat_at = job.finished_at
                job.result_json = {
                    "classification_run_id": run.id,
                    "classified_products": sum(value == "classified" for value in outcomes),
                    "products": len(outcomes),
                }

    @contextmanager
    def _heartbeat(self, job_id: int):
        stop = Event()

        def pulse() -> None:
            interval = max(5.0, min(30.0, self.settings.worker_stale_after_seconds / 3))
            while not stop.wait(interval):
                with self.sessions.begin() as session:
                    session.execute(
                        update(Job)
                        .where(
                            Job.id == job_id,
                            Job.worker_id == self.worker_id,
                            Job.status == ProcessingStatus.RUNNING.value,
                        )
                        .values(heartbeat_at=datetime.now(timezone.utc))
                    )

        thread = Thread(target=pulse, name=f"heartbeat-{job_id}", daemon=True)
        thread.start()
        try:
            yield
        finally:
            stop.set()
            thread.join(timeout=5)

    def run_forever(self) -> None:
        logger.info("worker_started", extra={"worker_id": self.worker_id})
        while True:
            if not self.run_once():
                time.sleep(self.settings.worker_poll_seconds)


def main() -> None:
    configure_logging()
    settings = get_settings()
    sessions = create_session_factory(settings)
    storage = FileStorage(settings.storage_root, settings.max_pdf_bytes)
    Worker(settings, sessions, storage).run_forever()


if __name__ == "__main__":
    main()
