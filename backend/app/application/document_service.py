"""Upload, deduplication and document history use cases."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import base64
import json
from typing import BinaryIO

from sqlalchemy import Date, cast, func, select, tuple_
from sqlalchemy.orm import Session

from backend.app.config import Settings
from backend.app.domain.enums import JobKind, ProcessingStatus
from backend.app.domain.errors import ApplicationError, NotFoundError
from backend.app.infrastructure.database.models import (
    ClassificationResult,
    ClassificationRun,
    Document,
    Heat,
    Job,
    Manufacturer,
    MillCertificate,
    Product,
    StoredFile,
)
from backend.app.infrastructure.files import FileStorage


@dataclass(frozen=True)
class UploadResult:
    document_id: int
    certificate_id: int
    job_id: int | None
    duplicate: bool


def encode_cursor(sort_date: date, identifier: int) -> str:
    raw = json.dumps([sort_date.isoformat(), identifier], separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_cursor(value: str) -> tuple[date, int]:
    try:
        padded = value + "=" * (-len(value) % 4)
        decoded = json.loads(base64.b64decode(padded, altchars=b"-_", validate=True).decode())
        if (not isinstance(decoded, list) or len(decoded) != 2
                or not isinstance(decoded[0], str)
                or type(decoded[1]) is not int or not 0 < decoded[1] <= 2**63 - 1):
            raise ValueError("Invalid cursor payload")
        return date.fromisoformat(decoded[0]), decoded[1]
    except Exception as exc:
        raise ApplicationError("invalid_cursor", "El cursor de paginación no es válido") from exc


def resolve_period_dates(period: str | None, today: date | None = None) -> tuple[date | None, date | None]:
    if not period or period in {"all", "custom"}:
        return None, None
    ref_date = today or datetime.now(timezone.utc).date()
    norm = period.strip().lower()
    if norm in {"day", "today"}:
        return ref_date, ref_date
    elif norm == "week":
        return ref_date - timedelta(days=7), ref_date
    elif norm == "month":
        return ref_date - timedelta(days=30), ref_date
    return None, None


class DocumentService:
    def __init__(self, settings: Settings, storage: FileStorage) -> None:
        self.settings = settings
        self.storage = storage

    def upload(self, session: Session, stream: BinaryIO, original_name: str) -> UploadResult:
        artifact = self.storage.store_document(stream, original_name)
        existing_file = session.scalar(select(StoredFile).where(StoredFile.sha256 == artifact.sha256))
        if existing_file is not None:
            document = session.scalar(
                select(Document).where(Document.stored_file_id == existing_file.id)
            )
            if document is not None:
                certificate = session.scalar(
                    select(MillCertificate).where(MillCertificate.document_id == document.id)
                )
                if certificate is None:
                    raise ApplicationError(
                        "document_incomplete",
                        "El documento existente no tiene un acta asociada",
                        status_code=500,
                    )
                job = session.scalar(
                    select(Job)
                    .where(Job.document_id == document.id)
                    .order_by(Job.id.desc())
                    .limit(1)
                )
                return UploadResult(
                    document.id,
                    certificate.id,
                    job.id if job else None,
                    True,
                )

        stored_file = existing_file or StoredFile(
            sha256=artifact.sha256,
            original_name=artifact.original_name,
            storage_name=artifact.storage_name,
            relative_path=artifact.relative_path,
            media_type=artifact.media_type,
            size_bytes=artifact.size_bytes,
            status="ready",
        )
        session.add(stored_file)
        session.flush()
        document = Document(stored_file_id=stored_file.id, processing_status="queued")
        session.add(document)
        session.flush()
        certificate = MillCertificate(
            document_id=document.id,
            approval_status="draft",
            demo_notice=self.settings.demo_notice,
        )
        session.add(certificate)
        job = Job(
            document_id=document.id,
            kind=JobKind.EXTRACT_DOCUMENT.value,
            status=ProcessingStatus.QUEUED.value,
            payload_json={},
        )
        session.add(job)
        session.flush()
        return UploadResult(document.id, certificate.id, job.id, False)

    def list_certificates(
        self,
        session: Session,
        *,
        limit: int,
        cursor: str | None = None,
        certificate_no: str | None = None,
        manufacturer: str | None = None,
        approval_status: str | None = None,
        processing_status: str | None = None,
        heat_no: str | None = None,
        product_identifier: str | None = None,
        fraction: str | None = None,
        nico: str | None = None,
        period: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        date_basis: str = "certificate",
    ) -> tuple[list[tuple[MillCertificate, Manufacturer | None]], str | None]:
        if period:
            p_from, p_to = resolve_period_dates(period)
            if p_from is not None:
                date_from = date_from or p_from
            if p_to is not None:
                date_to = date_to or p_to
        if date_from and date_to and date_from > date_to:
            raise ApplicationError("invalid_date_range", "La fecha inicial debe ser anterior o igual a la final")

        uploaded_date = cast(MillCertificate.uploaded_at, Date)
        sort_date = (
            uploaded_date
            if date_basis == "uploaded"
            else func.coalesce(MillCertificate.certificate_date, uploaded_date)
        )
        statement = (
            select(MillCertificate, Manufacturer)
            .outerjoin(Manufacturer, Manufacturer.id == MillCertificate.manufacturer_id)
            .join(Document, Document.id == MillCertificate.document_id)
            .where(Document.archived.is_(False))
        )
        if certificate_no:
            statement = statement.where(MillCertificate.certificate_no.ilike(f"%{certificate_no}%"))
        if manufacturer:
            statement = statement.where(Manufacturer.name.ilike(f"%{manufacturer}%"))
        if approval_status:
            statement = statement.where(MillCertificate.approval_status == approval_status)
        if processing_status:
            statement = statement.where(Document.processing_status == processing_status)
        if heat_no:
            statement = statement.where(
                MillCertificate.id.in_(
                    select(Heat.certificate_id).where(Heat.heat_no.ilike(f"%{heat_no}%"))
                )
            )
        if product_identifier:
            statement = statement.where(
                MillCertificate.id.in_(
                    select(Product.certificate_id).where(Product.product_identifier.ilike(f"%{product_identifier}%"))
                )
            )
        if fraction or nico:
            classifications = (
                select(ClassificationRun.certificate_id)
                .join(ClassificationResult, ClassificationResult.classification_run_id == ClassificationRun.id)
            )
            if fraction:
                clean_frac = fraction.replace(".", "").replace("-", "")
                classifications = classifications.where(ClassificationResult.fraction.ilike(f"{clean_frac}%"))
            if nico:
                classifications = classifications.where(ClassificationResult.nico == nico.strip())
            statement = statement.where(
                MillCertificate.id.in_(classifications)
            )
        if date_from:
            statement = statement.where(sort_date >= date_from)
        if date_to:
            statement = statement.where(sort_date <= date_to)
        if cursor:
            cursor_date, cursor_id = decode_cursor(cursor)
            statement = statement.where(tuple_(sort_date, MillCertificate.id) < (cursor_date, cursor_id))
        statement = statement.order_by(sort_date.desc(), MillCertificate.id.desc()).limit(limit + 1)
        rows = list(session.execute(statement).all())
        has_more = len(rows) > limit
        rows = rows[:limit]
        next_cursor = None
        if has_more and rows:
            certificate = rows[-1][0]
            value = (
                certificate.uploaded_at.date()
                if date_basis == "uploaded"
                else certificate.certificate_date or certificate.uploaded_at.date()
            )
            next_cursor = encode_cursor(value, certificate.id)
        return rows, next_cursor

    @staticmethod
    def get_certificate(session: Session, certificate_id: int) -> MillCertificate:
        certificate = session.get(MillCertificate, certificate_id)
        if certificate is None:
            raise NotFoundError("Acta", certificate_id)
        return certificate
