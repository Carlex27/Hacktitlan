"""Isolated draft library routes registered by the API composition root."""
from collections.abc import Callable, Iterator
from hashlib import sha256

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from backend.app.api.format_schemas import (
    FormatCreate, FormatDetail, FormatEnvelope, FormatJobRead, FormatRead, LayoutRead,
    PreviewRequest, PreviewRevision, PreviewTestRead, VersionCreate, VersionEdit, VersionRead,
)
from backend.app.api.schemas import ActorReason, ErrorEnvelope
from backend.app.application.format_jobs import LAYOUT_ADAPTER
from backend.app.application.format_activation import review_test, transition_version
from backend.app.application.format_service import (
    edit_version, enqueue_layout, enqueue_test, get_version, new_version, pdf_document,
)
from backend.app.domain.enums import ProcessingStatus
from backend.app.domain.errors import ApplicationError, ConflictError, NotFoundError
from backend.app.infrastructure.database.models import (
    CertificateFormat, CertificateFormatVersion, CertificateFormatTest, Job, PreparedDocumentLayout,
)
from backend.app.infrastructure.files import FileStorage
from backend.app.document_ingestion.page_image import render_page_image
from backend.app.certificate_parser.templates import extractor_hash


def version_read(version: CertificateFormatVersion) -> VersionRead:
    return VersionRead(id=version.id, format_id=version.format_id, version_number=version.version_number,
        revision=version.revision, status=version.status, configuration=version.configuration_json,
        configuration_sha256=version.configuration_sha256, person_name=version.person_name,
        reason=version.reason, updated_at=version.updated_at, lifecycle=version.lifecycle_json)


def format_router(storage: FileStorage, session_dependency: Callable[..., Iterator[Session]]) -> APIRouter:
    router = APIRouter(prefix="/api/v1", tags=["Certificate format drafts"], responses={
        404: {"model": ErrorEnvelope}, 409: {"model": ErrorEnvelope}, 422: {"model": ErrorEnvelope}})

    @router.get("/certificate-formats", response_model=FormatEnvelope[list[FormatRead]])
    def formats(limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0),
                q: str | None = Query(None, max_length=200),
                session: Session = Depends(session_dependency, scope="function")):
        query = select(CertificateFormat)
        if q and q.strip():
            query = query.where(or_(CertificateFormat.name.icontains(q.strip(), autoescape=True),
                                    CertificateFormat.description.icontains(q.strip(), autoescape=True)))
        rows = session.scalars(query.order_by(CertificateFormat.id).offset(offset).limit(limit)).all()
        return FormatEnvelope(data=[FormatRead(id=row.id, name=row.name, description=row.description) for row in rows],
                              meta={"limit": limit, "offset": offset})

    @router.post("/certificate-formats", response_model=FormatEnvelope[FormatRead], status_code=201)
    def create_format(payload: FormatCreate, session: Session = Depends(session_dependency, scope="function")):
        row = CertificateFormat(name=payload.name, description=payload.description)
        session.add(row)
        session.flush()
        # The initial empty draft carries the actor/reason supplied at creation.
        from backend.app.certificate_parser.templates import TemplateConfiguration
        new_version(session, row.id, TemplateConfiguration(), payload.person_name, payload.reason)
        return FormatEnvelope(data=FormatRead(id=row.id, name=row.name, description=row.description))

    @router.get("/certificate-formats/{format_id}", response_model=FormatEnvelope[FormatDetail])
    def format_detail(format_id: int, session: Session = Depends(session_dependency, scope="function")):
        row = session.get(CertificateFormat, format_id)
        if row is None:
            raise NotFoundError("Formato", format_id)
        versions = session.scalars(select(CertificateFormatVersion).where(
            CertificateFormatVersion.format_id == format_id).order_by(CertificateFormatVersion.version_number)).all()
        return FormatEnvelope(data=FormatDetail(id=row.id, name=row.name, description=row.description,
                                              versions=[version_read(v) for v in versions]))

    @router.post("/certificate-formats/{format_id}/versions", response_model=FormatEnvelope[VersionRead], status_code=201)
    def create_version(format_id: int, payload: VersionCreate, session: Session = Depends(session_dependency, scope="function")):
        return FormatEnvelope(data=version_read(new_version(session, format_id, payload.configuration,
                                                            payload.person_name, payload.reason)))

    @router.get("/certificate-format-versions/{version_id}", response_model=FormatEnvelope[VersionRead])
    def version_detail(version_id: int, session: Session = Depends(session_dependency, scope="function")):
        return FormatEnvelope(data=version_read(get_version(session, version_id)))

    @router.patch("/certificate-format-versions/{version_id}", response_model=FormatEnvelope[VersionRead])
    def update_version(version_id: int, payload: VersionEdit, session: Session = Depends(session_dependency, scope="function")):
        return FormatEnvelope(data=version_read(edit_version(session, version_id, payload.expected_revision,
            payload.configuration, payload.person_name, payload.reason)))

    @router.post("/certificate-format-versions/{version_id}/activate", response_model=FormatEnvelope[VersionRead])
    def activate(version_id: int, payload: PreviewRevision, session: Session = Depends(session_dependency, scope="function")):
        return FormatEnvelope(data=version_read(transition_version(session, version_id, payload.expected_revision,
            "active", payload.person_name, payload.reason)))

    @router.post("/certificate-format-versions/{version_id}/retire", response_model=FormatEnvelope[VersionRead])
    def retire(version_id: int, payload: PreviewRevision, session: Session = Depends(session_dependency, scope="function")):
        return FormatEnvelope(data=version_read(transition_version(session, version_id, payload.expected_revision,
            "retired", payload.person_name, payload.reason)))

    @router.post("/documents/{document_id}/layout-jobs", response_model=FormatEnvelope[FormatJobRead], status_code=202)
    def prepare_layout(document_id: int, payload: ActorReason, session: Session = Depends(session_dependency, scope="function")):
        job = enqueue_layout(session, document_id, payload.person_name, payload.reason)
        return FormatEnvelope(data=FormatJobRead(job_id=job.id))

    @router.get("/documents/{document_id}/layout", response_model=FormatEnvelope[LayoutRead])
    def document_layout(document_id: int, session: Session = Depends(session_dependency, scope="function")):
        pdf_document(session, document_id)
        layout = session.scalar(select(PreparedDocumentLayout).where(
            PreparedDocumentLayout.document_id == document_id).order_by(PreparedDocumentLayout.id.desc()).limit(1))
        if layout is None:
            raise ConflictError("layout_not_prepared", "Primero prepara el documento mediante un trabajo de layout")
        return FormatEnvelope(data=layout_read(layout, session))

    def layout_read(layout: PreparedDocumentLayout, session: Session) -> LayoutRead:
        _, stored = pdf_document(session, layout.document_id)
        if stored.sha256 != layout.document_sha256:
            raise ConflictError("layout_document_mismatch", "El layout no coincide con el archivo actual")
        return LayoutRead(id=layout.id, document_id=layout.document_id,
                          document_sha256=layout.document_sha256, document=LAYOUT_ADAPTER.validate_python(layout.layout_json))

    @router.get("/document-layouts/{layout_id}", response_model=FormatEnvelope[LayoutRead])
    def layout_detail(layout_id: int, session: Session = Depends(session_dependency, scope="function")):
        layout = session.get(PreparedDocumentLayout, layout_id)
        if layout is None:
            raise NotFoundError("Layout", layout_id)
        return FormatEnvelope(data=layout_read(layout, session))

    @router.get("/document-layouts/{layout_id}/pages/{page_number}/image", response_class=Response,
                responses={200: {"content": {"image/png": {}}}})
    def page_image(layout_id: int, page_number: int, session: Session = Depends(session_dependency, scope="function")):
        layout = session.get(PreparedDocumentLayout, layout_id)
        if layout is None:
            raise NotFoundError("Layout", layout_id)
        prepared = layout_read(layout, session).document
        page = next((page for page in prepared.pages if page.page_number == page_number), None)
        if page is None:
            raise NotFoundError("Página", page_number)
        _, stored = pdf_document(session, layout.document_id)
        path = storage.resolve(stored.relative_path)
        if sha256(path.read_bytes()).hexdigest() != layout.document_sha256:
            raise ConflictError("layout_document_mismatch", "El archivo cambió desde la preparación")
        rotations = prepared.metadata.get("ocr_page_rotations") or {}
        rotation = rotations.get(str(page_number), 0)
        if rotation == -1:
            rotation = 0
        try:
            image = render_page_image(path, page_number, rotation=rotation,
                                      expected_size=(page.width, page.height))
        except ValueError as exc:
            raise ApplicationError("layout_image_incompatible", str(exc), status_code=409) from exc
        return Response(image, media_type="image/png", headers={"Cache-Control": "no-store"})

    @router.post("/certificate-format-versions/{version_id}/tests", response_model=FormatEnvelope[PreviewTestRead], status_code=202)
    def create_test(version_id: int, payload: PreviewRequest, session: Session = Depends(session_dependency, scope="function")):
        test = enqueue_test(session, version_id, payload.expected_revision, payload.layout_id,
                            payload.person_name, payload.reason)
        return FormatEnvelope(data=test_read(test, session))

    def test_read(test: CertificateFormatTest, session: Session) -> PreviewTestRead:
        version = get_version(session, test.version_id)
        job = session.get(Job, test.job_id) if test.job_id else None
        return PreviewTestRead(id=test.id, version_id=test.version_id, document_id=test.document_id,
            layout_id=test.layout_id, job_id=test.job_id, revision=test.revision,
            configuration_sha256=test.configuration_sha256, extractor_sha256=test.extractor_sha256,
            status=ProcessingStatus(job.status) if job else ProcessingStatus.FAILED,
            result=test.result_json, current_revision=(test.revision == version.revision
                                                     and test.configuration_sha256 == version.configuration_sha256
                                                     and test.extractor_sha256 == extractor_hash()),
            reviewed_by=test.reviewed_by, review_reason=test.review_reason)

    @router.get("/certificate-format-versions/{version_id}/tests", response_model=FormatEnvelope[list[PreviewTestRead]])
    def version_tests(version_id: int, session: Session = Depends(session_dependency, scope="function")):
        get_version(session, version_id)
        tests = session.scalars(select(CertificateFormatTest).where(CertificateFormatTest.version_id == version_id)
                               .order_by(CertificateFormatTest.id.desc()).limit(100)).all()
        return FormatEnvelope(data=[test_read(t, session) for t in tests])

    @router.post("/certificate-format-tests/{test_id}/confirm", response_model=FormatEnvelope[PreviewTestRead])
    def confirm_test(test_id: int, payload: ActorReason, session: Session = Depends(session_dependency, scope="function")):
        return FormatEnvelope(data=test_read(review_test(session, test_id, payload.person_name, payload.reason), session))

    @router.get("/certificate-format-tests/{test_id}", response_model=FormatEnvelope[PreviewTestRead])
    def test_detail(test_id: int, session: Session = Depends(session_dependency, scope="function")):
        test = session.get(CertificateFormatTest, test_id)
        if test is None:
            raise NotFoundError("Prueba de formato", test_id)
        return FormatEnvelope(data=test_read(test, session))

    return router
