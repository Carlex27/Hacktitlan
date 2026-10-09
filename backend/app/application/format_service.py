"""Draft editing and immutable preview requests; no certificate writes."""
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from backend.app.certificate_parser.templates import TemplateConfiguration, extractor_hash
from backend.app.domain.enums import JobKind
from backend.app.domain.errors import ApplicationError, ConflictError, NotFoundError
from backend.app.infrastructure.database.models import (
    CertificateFormat, CertificateFormatVersion, CertificateFormatTest,
    Document, Job, PreparedDocumentLayout, StoredFile,
)


def get_version(session: Session, version_id: int) -> CertificateFormatVersion:
    version = session.get(CertificateFormatVersion, version_id)
    if version is None:
        raise NotFoundError("Versión de formato", version_id)
    return version


def new_version(session: Session, format_id: int, configuration: TemplateConfiguration,
                person_name: str, reason: str) -> CertificateFormatVersion:
    parent = session.scalar(select(CertificateFormat).where(CertificateFormat.id == format_id).with_for_update())
    if parent is None:
        raise NotFoundError("Formato", format_id)
    number = session.scalar(select(func.max(CertificateFormatVersion.version_number)).where(
        CertificateFormatVersion.format_id == format_id)) or 0
    version = CertificateFormatVersion(format_id=format_id, version_number=number + 1,
        configuration_json=configuration.model_dump(mode="json"), configuration_sha256=configuration.sha256,
        person_name=person_name, reason=reason)
    session.add(version)
    session.flush()
    return version


def edit_version(session: Session, version_id: int, revision: int, configuration: TemplateConfiguration,
                 person_name: str, reason: str) -> CertificateFormatVersion:
    get_version(session, version_id)
    result = session.execute(update(CertificateFormatVersion).where(
        CertificateFormatVersion.id == version_id, CertificateFormatVersion.revision == revision,
        CertificateFormatVersion.status == "draft").values(
            revision=revision + 1, configuration_json=configuration.model_dump(mode="json"),
            configuration_sha256=configuration.sha256, person_name=person_name, reason=reason))
    if result.rowcount != 1:
        raise ConflictError("format_revision_conflict", "El borrador cambió; vuelve a cargarlo antes de guardar")
    session.expire_all()
    return get_version(session, version_id)


def pdf_document(session: Session, document_id: int) -> tuple[Document, StoredFile]:
    document = session.get(Document, document_id)
    if document is None:
        raise NotFoundError("Documento", document_id)
    stored = session.get(StoredFile, document.stored_file_id)
    if stored is None:
        raise NotFoundError("Archivo", document.stored_file_id)
    if stored.media_type != "application/pdf":
        raise ApplicationError("format_requires_pdf", "El editor de formatos requiere un PDF", status_code=422)
    return document, stored


def enqueue_layout(session: Session, document_id: int, person_name: str, reason: str) -> Job:
    document, stored = pdf_document(session, document_id)
    job = Job(document_id=document.id, kind=JobKind.PREPARE_LAYOUT.value,
              payload_json={"document_sha256": stored.sha256, "person_name": person_name, "reason": reason})
    session.add(job)
    session.flush()
    return job


def enqueue_test(session: Session, version_id: int, revision: int, layout_id: int,
                 person_name: str, reason: str) -> CertificateFormatTest:
    version = session.scalar(select(CertificateFormatVersion).where(
        CertificateFormatVersion.id == version_id).with_for_update())
    if version is None:
        raise NotFoundError("Versión de formato", version_id)
    if version.revision != revision:
        raise ConflictError("format_revision_conflict", "La versión de la prueba no coincide con el borrador")
    layout = session.get(PreparedDocumentLayout, layout_id)
    if layout is None:
        raise NotFoundError("Layout preparado", layout_id)
    _, stored = pdf_document(session, layout.document_id)
    if layout.document_sha256 != stored.sha256:
        raise ConflictError("layout_document_mismatch", "El layout no corresponde al archivo actual")
    test = CertificateFormatTest(version_id=version.id, document_id=layout.document_id, layout_id=layout.id,
        revision=version.revision, configuration_json=version.configuration_json,
        configuration_sha256=version.configuration_sha256, extractor_sha256=extractor_hash())
    session.add(test)
    session.flush()
    job = Job(document_id=layout.document_id, kind=JobKind.TEST_CERTIFICATE_FORMAT.value,
              payload_json={"test_id": test.id, "person_name": person_name, "reason": reason})
    session.add(job)
    session.flush()
    test.job_id = job.id
    return test
