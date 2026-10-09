"""Review, activation and queue snapshots for the local shared library."""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.application.format_service import get_version
from backend.app.application.format_jobs import LAYOUT_ADAPTER
from backend.app.certificate_parser.templates import TemplateConfiguration, extractor_hash
from backend.app.certificate_parser.template_recognition import TemplateSnapshot, matches_template
from backend.app.domain.errors import ConflictError, NotFoundError
from backend.app.infrastructure.database.models import CertificateFormat, CertificateFormatVersion, CertificateFormatTest, PreparedDocumentLayout, Job


def review_test(session: Session, test_id: int, person: str, reason: str) -> CertificateFormatTest:
    test = session.scalar(select(CertificateFormatTest).where(CertificateFormatTest.id == test_id).with_for_update())
    if test is None:
        raise NotFoundError("Prueba", test_id)
    version = get_version(session, test.version_id)
    job = session.get(Job, test.job_id)
    if (not job or job.status != "succeeded" or not test.result_json or test.result_json.get("status") != "success"
            or version.revision != test.revision or version.configuration_sha256 != test.configuration_sha256
            or test.extractor_sha256 != extractor_hash()):
        raise ConflictError("format_test_not_eligible", "Revisa una prueba terminada sin incidencias de la configuración actual")
    if test.reviewed_by is None:
        test.reviewed_by, test.review_reason = person, reason
    return test


def transition_version(session: Session, version_id: int, revision: int, action: str, person: str, reason: str):
    initial = get_version(session, version_id)
    session.scalar(select(CertificateFormat).where(CertificateFormat.id == initial.format_id).with_for_update())
    version = session.scalar(select(CertificateFormatVersion).where(CertificateFormatVersion.id == version_id)
                             .with_for_update().execution_options(populate_existing=True))
    if version.revision != revision:
        raise ConflictError("format_revision_conflict", "La versión cambió; vuelve a cargarla")
    if action == "active":
        if version.status != "draft":
            raise ConflictError("format_not_draft", "Crea un nuevo borrador para activar otra configuración")
        config = TemplateConfiguration.model_validate(version.configuration_json)
        anchors = {(a.page_number, a.text.casefold()) for a in config.recognition}
        if len(anchors) < 2 or not (config.fields or config.tables):
            raise ConflictError("format_recognition_required", "Configura al menos dos encabezados estables y asignaciones")
        tests = session.scalars(select(CertificateFormatTest).where(
            CertificateFormatTest.version_id == version.id, CertificateFormatTest.revision == version.revision,
            CertificateFormatTest.configuration_sha256 == version.configuration_sha256,
            CertificateFormatTest.extractor_sha256 == extractor_hash(), CertificateFormatTest.reviewed_by.is_not(None))).all()
        hashes = set()
        validation = []
        for test in tests:
            layout = session.get(PreparedDocumentLayout, test.layout_id)
            if (layout and test.result_json and test.result_json.get("status") == "success"
                    and (test.result_json.get("certificate") or {}).get("products")
                    and matches_template(LAYOUT_ADAPTER.validate_python(layout.layout_json), config)):
                hashes.add(layout.document_sha256)
                validation.append({"test_id": test.id, "document_sha256": layout.document_sha256,
                                   "reviewed_by": test.reviewed_by, "review_reason": test.review_reason})
        if len(hashes) < 3:
            raise ConflictError("format_validation_required", "Confirma pruebas sin incidencias sobre tres PDFs distintos con los encabezados configurados")
        previous = session.scalar(select(CertificateFormatVersion).where(
            CertificateFormatVersion.format_id == version.format_id, CertificateFormatVersion.status == "active").with_for_update())
        if previous:
            record_transition(previous, "retired", person, reason)
            session.flush()
    elif version.status != "active":
        raise ConflictError("format_not_active", "Sólo se puede retirar una versión activa")
    record_transition(version, action, person, reason)
    if action == "active":
        events = list(version.lifecycle_json)
        events[-1] = {**events[-1], "configuration_sha256": version.configuration_sha256,
                      "extractor_sha256": extractor_hash(), "validation": validation}
        version.lifecycle_json = events
    session.flush()
    return version


def record_transition(version, status, person, reason):
    version.status = status
    version.lifecycle_json = [*version.lifecycle_json, {"status": status, "person_name": person,
        "reason": reason, "at": datetime.now(timezone.utc).isoformat()}]


def template_snapshots(session: Session, version_id: int | None = None) -> list[dict]:
    query = select(CertificateFormatVersion).where(CertificateFormatVersion.status == "active")
    if version_id is not None:
        query = query.where(CertificateFormatVersion.id == version_id)
    versions = session.scalars(query.order_by(CertificateFormatVersion.id)).all()
    if version_id is not None and not versions:
        raise ConflictError("format_not_active", "Selecciona una versión activa")
    current_hash = extractor_hash()
    eligible = [v for v in versions if any(event.get("status") == "active" and event.get("extractor_sha256") == current_hash
                                           for event in v.lifecycle_json)]
    if version_id is not None and not eligible:
        raise ConflictError("format_extractor_changed", "El extractor cambió; crea, prueba y activa una nueva versión del formato")
    return [TemplateSnapshot(version_id=v.id, format_id=v.format_id, version_number=v.version_number,
        configuration=v.configuration_json, configuration_sha256=v.configuration_sha256,
        extractor_sha256=current_hash).model_dump(mode="json") for v in eligible]
