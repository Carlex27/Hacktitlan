"""FastAPI composition root and public API v1."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
import logging
import time
from typing import Any, Annotated, Literal
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Query, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy import false
from sqlalchemy import Date, and_, cast, exists, func, select, text, tuple_
from sqlalchemy.orm import Session, sessionmaker

from backend.app.api.schemas import (
    ActorReason,
    ArchiveRequest,
    CandidateDetailEnvelope,
    CandidateSelectionEnvelope,
    CandidateSelectionRequest,
    CorrectionRequest,
    DocumentQualityReportEnvelope,
    DocumentReviewQueueEnvelope,
    Envelope,
    ErrorEnvelope,
    ExportRequest,
    ManualObservationRequest,
    ReclassificationRequest,
    ReprocessEnvelope,
    ReprocessRequest,
)
from backend.app.application.document_quality_service import DocumentQualityService
from backend.app.application.document_service import DocumentService, decode_cursor, encode_cursor

from backend.app.application.review_service import ReviewService
from backend.app.config import Settings, get_settings
from backend.app.domain.enums import ApprovalStatus
from backend.app.domain.errors import ApplicationError, NotFoundError
from backend.app.infrastructure.database.models import (
    ChemicalComposition,
    CandidateFactor,
    ClassificationCandidate,
    ClassificationResult,
    ClassificationRun,
    ClassificationSelection,
    DecisionStep,
    Document,
    EvidenceLink,
    Export,
    Heat,
    Job,
    Manufacturer,
    MillCertificate,
    Observation,
    Product,
    StoredFile,
)
from backend.app.infrastructure.database.session import create_session_factory
from backend.app.infrastructure.files import FileStorage
from backend.app.infrastructure.logging import configure_logging
from backend.app.infrastructure.ocr import (
    OcrModelManager,
    probe_ocr_runtime,
    run_smoke_check,
)

logger = logging.getLogger(__name__)


def serialize_candidate_factor(
    factor: CandidateFactor,
    evidence_links: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "id": factor.id,
        "sequence": factor.sequence,
        "rule_code": factor.rule_code,
        "outcome": factor.outcome,
        "operator": factor.operator,
        "expected": factor.expected_json,
        "observed": factor.observed_json,
        "unit": factor.unit,
        "explanation": factor.explanation,
        "required_for_selection": factor.required_for_selection,
        "evidence_links": evidence_links,
    }


def ok(data: Any = None, *, meta: dict[str, Any] | None = None, status_code: int = 200) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"data": data, "meta": meta or {}, "error": None},
    )


def get_session(request: Request):
    factory: sessionmaker[Session] = request.app.state.sessions
    with factory() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise


DbSession = Annotated[Session, Depends(get_session)]


def serialize_certificate(certificate: MillCertificate, manufacturer: Manufacturer | None) -> dict[str, Any]:
    return {
        "id": certificate.id,
        "document_id": certificate.document_id,
        "manufacturer": manufacturer.name if manufacturer else None,
        "certificate_no": certificate.certificate_no,
        "certificate_date": certificate.certificate_date.isoformat() if certificate.certificate_date else None,
        "uploaded_at": certificate.uploaded_at.isoformat(),
        "revision_number": certificate.revision_number,
        "previous_revision_id": certificate.previous_revision_id,
        "approval_status": certificate.approval_status,
        "standard": certificate.standard,
        "product_name": certificate.product_name,
        "demo_notice": certificate.demo_notice,
    }


def create_app(settings: Settings | None = None) -> FastAPI:
    configure_logging()
    settings = settings or get_settings()
    sessions = create_session_factory(settings)
    storage = FileStorage(settings.storage_root, settings.max_pdf_bytes)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.settings = settings
        app.state.sessions = sessions
        app.state.storage = storage
        yield
        sessions.kw["bind"].dispose()

    app = FastAPI(title="Hacktitlan Mill Certificates API", version="1.0.0", lifespan=lifespan)
    app.state.settings = settings
    app.state.sessions = sessions
    app.state.storage = storage

    @app.middleware("http")
    async def correlation_id(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or uuid4().hex
        started = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "http_request",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            },
        )
        return response

    # Registrado después del middleware de correlación para que sea el más externo
    # y también agregue encabezados CORS a respuestas de error.
    # Lista explícita (HACKTITLAN_CORS_ORIGINS): el API no tiene autenticación, así
    # que "*" permitiría a cualquier página web abierta en la red aprobar, rechazar
    # o subir documentos. Para otro cliente, agregue su origen a la variable.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID", "Content-Disposition"],
    )

    @app.exception_handler(ApplicationError)
    async def application_error(_request: Request, exc: ApplicationError):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "data": None,
                "meta": {},
                "error": {"code": exc.code, "message": exc.message, "details": exc.details},
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(_request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={
                "data": None,
                "meta": {},
                "error": {
                    "code": "validation_error",
                    "message": "La solicitud contiene datos inválidos",
                    "details": {"issues": jsonable_encoder(exc.errors())},
                },
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error(_request: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "data": None,
                "meta": {},
                "error": {"code": "http_error", "message": str(exc.detail), "details": {}},
            },
        )

    @app.exception_handler(Exception)
    async def unexpected_error(_request: Request, exc: Exception):
        logger.exception("unhandled_error")
        return JSONResponse(
            status_code=500,
            content={
                "data": None,
                "meta": {},
                "error": {
                    "code": "internal_error",
                    "message": "Ocurrió un error interno",
                    "details": {},
                },
            },
        )

    @app.get("/api/v1/health/live")
    def live():
        return ok({"status": "ok"})

    @app.get("/api/v1/health/ready")
    def ready(session: DbSession):
        session.execute(text("SELECT 1"))
        settings.storage_root.mkdir(parents=True, exist_ok=True)
        return ok({"status": "ready", "database": "available", "storage": "available"})

    @app.get("/api/v1/ocr/status")
    def ocr_status():
        return ok(probe_ocr_runtime(settings).as_dict())

    @app.get("/api/v1/ocr/models")
    def ocr_models():
        return ok(OcrModelManager(settings.model_root).get_status().as_dict())

    @app.post("/api/v1/ocr/smoke-check")
    def ocr_smoke_check():
        return ok(run_smoke_check(settings))

    @app.post("/api/v1/documents", status_code=status.HTTP_202_ACCEPTED)
    def upload_document(request: Request, session: DbSession, file: UploadFile = File(...)):
        result = DocumentService(settings, request.app.state.storage).upload(
            session, file.file, file.filename or "document.pdf"
        )
        return ok(
            {
                "document_id": result.document_id,
                "certificate_id": result.certificate_id,
                "job_id": result.job_id,
                "duplicate": result.duplicate,
            },
            status_code=200 if result.duplicate else 202,
        )

    @app.get("/api/v1/certificates")
    def list_certificates(
        session: DbSession,
        limit: int = Query(50, ge=1, le=200),
        cursor: str | None = None,
        certificate_no: str | None = None,
        manufacturer: str | None = None,
        approval_status: ApprovalStatus | None = None,
        processing_status: str | None = None,
        heat_no: str | None = None,
        product_identifier: str | None = None,
        fraction: str | None = None,
        nico: str | None = None,
        period: Literal["day", "today", "week", "month"] | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        date_basis: Literal["certificate", "uploaded"] = "certificate",
    ):
        rows, next_cursor = DocumentService(settings, storage).list_certificates(
            session,
            limit=limit,
            cursor=cursor,
            certificate_no=certificate_no,
            manufacturer=manufacturer,
            approval_status=approval_status,
            processing_status=processing_status,
            heat_no=heat_no,
            product_identifier=product_identifier,
            fraction=fraction,
            nico=nico,
            period=period,
            date_from=date_from,
            date_to=date_to,
            date_basis=date_basis,
        )
        return ok(
            [serialize_certificate(certificate, maker) for certificate, maker in rows],
            meta={
                "next_cursor": next_cursor,
                "limit": limit,
                "date_basis": date_basis,
                "period": period,
                "filters": {
                    k: v for k, v in {
                        "certificate_no": certificate_no,
                        "manufacturer": manufacturer,
                        "approval_status": approval_status.value if approval_status else None,
                        "processing_status": processing_status,
                        "heat_no": heat_no,
                        "product_identifier": product_identifier,
                        "fraction": fraction,
                        "nico": nico,
                        "period": period,
                        "date_from": date_from.isoformat() if date_from else None,
                        "date_to": date_to.isoformat() if date_to else None,
                    }.items() if v is not None
                },
            },
        )

    @app.get("/api/v1/certificates/{certificate_id}")
    def certificate_detail(certificate_id: int, session: DbSession):
        certificate = DocumentService.get_certificate(session, certificate_id)
        manufacturer = session.get(Manufacturer, certificate.manufacturer_id) if certificate.manufacturer_id else None
        heats = session.scalars(select(Heat).where(Heat.certificate_id == certificate.id).order_by(Heat.id)).all()
        products = session.scalars(select(Product).where(Product.certificate_id == certificate.id).order_by(Product.id)).all()
        observations = session.scalars(
            select(Observation).where(Observation.certificate_id == certificate.id).order_by(Observation.id)
        ).all()
        heat_ids = [heat.id for heat in heats]
        product_ids = [product.id for product in products]
        heat_filter = ChemicalComposition.heat_id.in_(heat_ids) if heat_ids else false()
        product_filter = ChemicalComposition.product_id.in_(product_ids) if product_ids else false()
        chemistry = session.scalars(
            select(ChemicalComposition).where(heat_filter | product_filter).order_by(ChemicalComposition.id)
        ).all()
        data = serialize_certificate(certificate, manufacturer)
        data.update({
            "heats": [{"id": h.id, "heat_no": h.heat_no, "standard": h.standard, "grade": h.grade} for h in heats],
            "products": [{
                "id": p.id, "heat_id": p.heat_id, "product_identifier": p.product_identifier,
                "label_no": p.label_no, "product_type": p.product_type, "form": p.form,
                "coiled": p.coiled, "rolling": p.rolling,
                "width_mm": str(p.width_mm) if p.width_mm is not None else None,
                "thickness_mm": str(p.thickness_mm) if p.thickness_mm is not None else None,
                "weight_kg": str(p.weight_kg) if p.weight_kg is not None else None,
            } for p in products],
            "observations": [{
                "id": o.id, "heat_id": o.heat_id, "product_id": o.product_id,
                "field_path": o.field_path, "raw_value": o.raw_value_json,
                "normalized_value": o.normalized_value_json, "unit": o.unit,
                "confidence": o.confidence, "page_number": o.page_number,
                "bbox": o.bbox_json, "source_text": o.source_text,
                "inherited": o.inherited, "supersedes_id": o.supersedes_id,
                "is_current": o.is_current,
            } for o in observations],
            "chemical_compositions": [{
                "id": c.id, "heat_id": c.heat_id, "product_id": c.product_id,
                "element": c.element, "raw_value": c.raw_value_json,
                "percentage": str(c.percentage) if c.percentage is not None else None,
                "inherited": c.inherited, "source_label": c.source_label,
            } for c in chemistry],
        })
        return ok(data)

    @app.get(
        "/api/v1/certificates/{certificate_id}/quality-report",
        responses={
            200: {"model": DocumentQualityReportEnvelope, "description": "Reporte de calidad y validación documental"},
            404: {"model": ErrorEnvelope, "description": "Acta no encontrada"},
        },
    )
    def certificate_quality_report(certificate_id: int, session: DbSession):
        report = DocumentQualityService(settings).evaluate_certificate(session, certificate_id)
        return ok(report.as_dict())

    @app.get(
        "/api/v1/document-reviews",
        responses={
            200: {"model": DocumentReviewQueueEnvelope, "description": "Cola de revisión documental con incidencias"},
        },
    )
    def list_document_reviews(
        session: DbSession,
        limit: int = Query(50, ge=1, le=200),
        status_filter: str | None = Query(None),
    ):
        items = DocumentQualityService(settings).get_review_queue(
            session,
            limit=limit,
            status_filter=status_filter,
        )
        return ok(items, meta={"limit": limit, "count": len(items)})


    @app.get("/api/v1/heats")
    def list_heats(
        session: DbSession,
        limit: int = Query(50, ge=1, le=200),
        cursor: str | None = None,
        heat_no: str | None = None,
        certificate_no: str | None = None,
        manufacturer: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        date_basis: Literal["certificate", "uploaded"] = "certificate",
    ):
        uploaded_date = cast(MillCertificate.uploaded_at, Date)
        sort_date = uploaded_date if date_basis == "uploaded" else func.coalesce(MillCertificate.certificate_date, uploaded_date)
        query = (
            select(Heat, MillCertificate, Manufacturer)
            .join(MillCertificate, MillCertificate.id == Heat.certificate_id)
            .outerjoin(Manufacturer, Manufacturer.id == MillCertificate.manufacturer_id)
        )
        if heat_no:
            query = query.where(Heat.heat_no.ilike(f"%{heat_no}%"))
        if certificate_no:
            query = query.where(MillCertificate.certificate_no.ilike(f"%{certificate_no}%"))
        if manufacturer:
            query = query.where(Manufacturer.name.ilike(f"%{manufacturer}%"))
        if date_from:
            query = query.where(sort_date >= date_from)
        if date_to:
            query = query.where(sort_date <= date_to)
        if cursor:
            cursor_date, cursor_id = decode_cursor(cursor)
            query = query.where(tuple_(sort_date, Heat.id) < (cursor_date, cursor_id))
        rows = list(session.execute(query.order_by(sort_date.desc(), Heat.id.desc()).limit(limit + 1)).all())
        has_more = len(rows) > limit
        rows = rows[:limit]
        next_cursor = None
        if has_more and rows:
            heat, certificate, _ = rows[-1]
            cursor_date = certificate.uploaded_at.date() if date_basis == "uploaded" else certificate.certificate_date or certificate.uploaded_at.date()
            next_cursor = encode_cursor(cursor_date, heat.id)
        return ok([{
            "id": heat.id, "certificate_id": certificate.id, "certificate_no": certificate.certificate_no,
            "certificate_date": certificate.certificate_date.isoformat() if certificate.certificate_date else None,
            "manufacturer": maker.name if maker else None, "heat_no": heat.heat_no,
            "standard": heat.standard, "grade": heat.grade, "properties": heat.properties_json,
        } for heat, certificate, maker in rows], meta={"next_cursor": next_cursor, "limit": limit, "date_basis": date_basis})

    @app.get("/api/v1/products")
    def list_products(
        session: DbSession,
        limit: int = Query(50, ge=1, le=200),
        cursor: str | None = None,
        product_identifier: str | None = None,
        heat_no: str | None = None,
        certificate_no: str | None = None,
        fraction: str | None = None,
        nico: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        date_basis: Literal["certificate", "uploaded"] = "certificate",
    ):
        uploaded_date = cast(MillCertificate.uploaded_at, Date)
        sort_date = uploaded_date if date_basis == "uploaded" else func.coalesce(MillCertificate.certificate_date, uploaded_date)
        query = (
            select(Product, Heat, MillCertificate)
            .join(MillCertificate, MillCertificate.id == Product.certificate_id)
            .outerjoin(Heat, Heat.id == Product.heat_id)
        )
        if fraction or nico:
            classification_filters = [
                ClassificationResult.product_id == Product.id,
                ClassificationRun.id == ClassificationResult.classification_run_id,
                ClassificationRun.approval_status == ApprovalStatus.APPROVED.value,
            ]
            if fraction:
                classification_filters.append(ClassificationResult.fraction == fraction)
            if nico:
                classification_filters.append(ClassificationResult.nico == nico)
            query = query.where(
                exists(select(1).select_from(ClassificationResult, ClassificationRun).where(and_(*classification_filters)))
            )
        if product_identifier:
            query = query.where(Product.product_identifier.ilike(f"%{product_identifier}%"))
        if heat_no:
            query = query.where(Heat.heat_no.ilike(f"%{heat_no}%"))
        if certificate_no:
            query = query.where(MillCertificate.certificate_no.ilike(f"%{certificate_no}%"))
        if date_from:
            query = query.where(sort_date >= date_from)
        if date_to:
            query = query.where(sort_date <= date_to)
        if cursor:
            cursor_date, cursor_id = decode_cursor(cursor)
            query = query.where(tuple_(sort_date, Product.id) < (cursor_date, cursor_id))
        rows = list(session.execute(query.order_by(sort_date.desc(), Product.id.desc()).limit(limit + 1)).all())
        has_more = len(rows) > limit
        rows = rows[:limit]
        next_cursor = None
        if has_more and rows:
            product, _, certificate = rows[-1]
            cursor_date = certificate.uploaded_at.date() if date_basis == "uploaded" else certificate.certificate_date or certificate.uploaded_at.date()
            next_cursor = encode_cursor(cursor_date, product.id)
        return ok([{
            "id": product.id, "certificate_id": certificate.id, "certificate_no": certificate.certificate_no,
            "heat_id": product.heat_id, "heat_no": heat.heat_no if heat else None,
            "product_identifier": product.product_identifier, "label_no": product.label_no,
            "product_type": product.product_type, "form": product.form, "coiled": product.coiled,
            "rolling": product.rolling, "width_mm": str(product.width_mm) if product.width_mm is not None else None,
            "thickness_mm": str(product.thickness_mm) if product.thickness_mm is not None else None,
            "weight_kg": str(product.weight_kg) if product.weight_kg is not None else None,
        } for product, heat, certificate in rows], meta={"next_cursor": next_cursor, "limit": limit, "date_basis": date_basis})

    @app.get("/api/v1/documents/{document_id}/file")
    def download_document(document_id: int, request: Request, session: DbSession):
        document = session.get(Document, document_id)
        if document is None:
            raise NotFoundError("Documento", document_id)
        stored = session.get(StoredFile, document.stored_file_id)
        if stored is None:
            raise NotFoundError("Archivo", document.stored_file_id)
        path = request.app.state.storage.resolve(stored.relative_path)
        # `inline` permite mostrar el PDF en el visor de la app; el nombre se conserva
        # para "Guardar como".
        return FileResponse(
            path,
            media_type=stored.media_type,
            filename=stored.original_name,
            content_disposition_type="inline",
        )

    @app.get("/api/v1/evidence/{evidence_link_id}")
    def evidence_detail(evidence_link_id: int, session: DbSession):
        link = session.get(EvidenceLink, evidence_link_id)
        if link is None:
            raise NotFoundError("Enlace de evidencia", evidence_link_id)
        if link.source_type == "rule_source":
            return ok({
                "id": link.id,
                "decision_step_id": link.decision_step_id,
                "candidate_factor_id": link.candidate_factor_id,
                "source_type": link.source_type,
                "reference": link.source_reference_json,
            })

        observation = session.get(Observation, link.observation_id)
        if observation is None:
            raise NotFoundError("Observación de evidencia", link.observation_id)
        certificate = session.get(MillCertificate, observation.certificate_id)
        if certificate is None:
            raise NotFoundError("Acta de evidencia", observation.certificate_id)
        can_focus_region = observation.page_number is not None and observation.bbox_json is not None
        return ok({
            "id": link.id,
            "decision_step_id": link.decision_step_id,
            "candidate_factor_id": link.candidate_factor_id,
            "source_type": link.source_type,
            "field_path": link.field_path,
            "observation": {
                "id": observation.id,
                "raw_value": observation.raw_value_json,
                "normalized_value": observation.normalized_value_json,
                "unit": observation.unit,
                "confidence": observation.confidence,
                "source_text": observation.source_text,
            },
            "document": {
                "id": certificate.document_id,
                "file_url": f"/api/v1/documents/{certificate.document_id}/file",
            },
            "focus": {
                "page_number": observation.page_number,
                "bbox": observation.bbox_json,
                "can_focus_region": can_focus_region,
                "fallback": None if can_focus_region else "full_page",
            },
        })

    @app.get(
        "/api/v1/classification-candidates/{candidate_id}",
        responses={
            200: {"model": CandidateDetailEnvelope, "description": "Detalle del candidato con factores y evidencia"},
            404: {"model": ErrorEnvelope, "description": "Candidato no encontrado"},
        },
    )
    def classification_candidate_detail(candidate_id: int, session: DbSession):
        candidate = session.get(ClassificationCandidate, candidate_id)
        if candidate is None:
            raise NotFoundError("Candidato de clasificación", candidate_id)
        factors = session.scalars(
            select(CandidateFactor)
            .where(CandidateFactor.candidate_id == candidate.id)
            .order_by(CandidateFactor.sequence)
        ).all()
        factor_ids = [factor.id for factor in factors]
        links = session.scalars(
            select(EvidenceLink)
            .where(EvidenceLink.candidate_factor_id.in_(factor_ids))
            .order_by(EvidenceLink.candidate_factor_id, EvidenceLink.id)
        ).all() if factor_ids else []
        links_by_factor: dict[int, list[dict[str, Any]]] = {}
        for link in links:
            assert link.candidate_factor_id is not None
            links_by_factor.setdefault(link.candidate_factor_id, []).append({
                "id": link.id,
                "source_type": link.source_type,
                "field_path": link.field_path,
                "observation_id": link.observation_id,
                "reference": link.source_reference_json,
                "detail_url": f"/api/v1/evidence/{link.id}",
            })
        return ok({
            "id": candidate.id,
            "classification_result_id": candidate.classification_result_id,
            "rank": candidate.rank,
            "fraction": candidate.fraction,
            "nico": candidate.nico,
            "description": candidate.description,
            "support_level": candidate.support_level,
            "details": candidate.details_json,
            "factors": [
                serialize_candidate_factor(factor, links_by_factor.get(factor.id, []))
                for factor in factors
            ],
        })

    @app.post("/api/v1/documents/{document_id}/archive")
    def archive_document(document_id: int, payload: ArchiveRequest, session: DbSession):
        document = session.get(Document, document_id)
        if document is None:
            raise NotFoundError("Documento", document_id)
        metadata = dict(document.metadata_json or {})
        events = list(metadata.get("archive_events") or [])
        events.append({
            "archived": payload.archived,
            "person_name": payload.person_name,
            "reason": payload.reason,
            "workstation_name": settings.workstation_name,
            "occurred_at": datetime.now(timezone.utc).isoformat(),
        })
        metadata["archive_events"] = events
        document.metadata_json = metadata
        document.archived = payload.archived
        return ok({"document_id": document.id, "archived": document.archived})

    @app.get("/api/v1/jobs/{job_id}")
    def job_detail(job_id: int, session: DbSession):
        job = session.get(Job, job_id)
        if job is None:
            raise NotFoundError("Trabajo", job_id)
        return ok({
            "id": job.id, "document_id": job.document_id, "kind": job.kind,
            "status": job.status, "progress": job.progress, "attempts": job.attempts,
            "max_attempts": job.max_attempts, "error_code": job.error_code,
            "error_message": job.error_message, "result": job.result_json,
        })

    @app.post("/api/v1/jobs/{job_id}/cancel")
    def cancel_job(job_id: int, payload: ActorReason, session: DbSession):
        job = session.get(Job, job_id)
        if job is None:
            raise NotFoundError("Trabajo", job_id)
        if job.status != "queued":
            raise ApplicationError(
                "job_not_cancellable",
                "Sólo se puede cancelar un trabajo que todavía está en cola",
                status_code=409,
            )
        job.status = "cancelled"
        job.finished_at = datetime.now(timezone.utc)
        job.result_json = {
            "cancelled_by": payload.person_name,
            "reason": payload.reason,
            "workstation_name": settings.workstation_name,
        }
        export_id = job.payload_json.get("export_id")
        export = session.get(Export, export_id) if export_id else None
        if export is not None:
            export.status = "failed"
            export.error_message = "Cancelada por la persona solicitante"
        return ok({"job_id": job.id, "status": job.status})

    @app.post("/api/v1/exports", status_code=status.HTTP_202_ACCEPTED)
    def request_export(payload: ExportRequest, session: DbSession):
        certificate_ids = list(dict.fromkeys(payload.certificate_ids))
        heat_ids = list(dict.fromkeys(payload.heat_ids))
        run_ids = list(dict.fromkeys(payload.classification_run_ids))
        existing_count = session.scalar(
            select(func.count(MillCertificate.id)).where(MillCertificate.id.in_(certificate_ids))
        ) if certificate_ids else 0
        if existing_count != len(certificate_ids):
            raise ApplicationError("invalid_export_scope", "Una o más actas seleccionadas no existen")
        selected_heats = session.scalars(select(Heat).where(Heat.id.in_(heat_ids))).all() if heat_ids else []
        if len(selected_heats) != len(heat_ids):
            raise ApplicationError("invalid_export_scope", "Una o más coladas seleccionadas no existen")
        certificate_ids = list(dict.fromkeys(certificate_ids + [heat.certificate_id for heat in selected_heats]))
        selected_runs = session.scalars(
            select(ClassificationRun).where(ClassificationRun.id.in_(run_ids))
        ).all() if run_ids else []
        if len(selected_runs) != len(run_ids):
            raise ApplicationError("invalid_export_scope", "Una o más ejecuciones seleccionadas no existen")
        certificate_ids = list(dict.fromkeys(
            certificate_ids + [run.certificate_id for run in selected_runs]
        ))
        if payload.official:
            unapproved = session.scalars(
                select(MillCertificate.id)
                .where(MillCertificate.id.in_(certificate_ids), MillCertificate.approval_status != "approved")
            ).all()
            if unapproved:
                raise ApplicationError(
                    "official_export_requires_approval",
                    f"Un reporte oficial sólo admite actas aprobadas (actas pendientes: {list(unapproved)})",
                    status_code=409,
                )
            if run_ids:
                unapproved_runs = session.scalars(
                    select(ClassificationRun.id)
                    .where(ClassificationRun.id.in_(run_ids), ClassificationRun.approval_status != "approved")
                ).all()
                if unapproved_runs:
                    raise ApplicationError(
                        "official_export_requires_approval",
                        f"Un reporte oficial sólo admite ejecuciones aprobadas (ejecuciones pendientes: {list(unapproved_runs)})",
                        status_code=409,
                    )
        export = Export(
            format="xlsx",
            status="queued",
            scope_json={
                "certificate_ids": certificate_ids,
                "heat_ids": heat_ids,
                "classification_run_ids": run_ids,
                "official": payload.official,
            },
            filters_json=payload.filters or {},
            person_name=payload.person_name,
            workstation_name=payload.workstation_name or settings.workstation_name,
        )
        session.add(export)
        session.flush()
        job = Job(
            kind="export_xlsx",
            status="queued",
            payload_json={"export_id": export.id},
        )
        session.add(job)
        session.flush()
        return ok({"export_id": export.id, "job_id": job.id}, status_code=202)

    @app.get("/api/v1/exports/{export_id}")
    def get_export_status(export_id: int, session: DbSession):
        export = session.get(Export, export_id)
        if export is None:
            raise NotFoundError("Exportación", export_id)
        return ok({
            "id": export.id,
            "format": export.format,
            "status": export.status,
            "scope": export.scope_json,
            "filters": export.filters_json,
            "person_name": export.person_name,
            "workstation_name": export.workstation_name,
            "sha256": export.sha256,
            "stored_file_id": export.stored_file_id,
            "error_message": export.error_message,
            "created_at": export.created_at.isoformat(),
            "download_url": f"/api/v1/exports/{export.id}/file" if export.status == "succeeded" else None,
        })

    @app.get("/api/v1/exports/{export_id}/file")
    def download_export(export_id: int, request: Request, session: DbSession):
        export = session.get(Export, export_id)
        if export is None:
            raise NotFoundError("Exportación", export_id)
        if export.status != "succeeded" or export.stored_file_id is None:
            raise ApplicationError("export_not_ready", "La exportación todavía no está disponible", status_code=409)
        stored = session.get(StoredFile, export.stored_file_id)
        if stored is None:
            raise NotFoundError("Archivo", export.stored_file_id)
        path = request.app.state.storage.resolve(stored.relative_path)
        return FileResponse(path, media_type=stored.media_type, filename=stored.original_name)

    @app.post("/api/v1/observations/{observation_id}/corrections")
    def correct_observation(observation_id: int, payload: CorrectionRequest, session: DbSession):
        observation = ReviewService(settings).correct_observation(
            session,
            observation_id=observation_id,
            normalized_value=payload.normalized_value,
            raw_value=payload.raw_value,
            unit=payload.unit,
            person_name=payload.person_name,
            reason=payload.reason,
        )
        return ok({"observation_id": observation.id, "supersedes_id": observation.supersedes_id})

    @app.post("/api/v1/certificates/{certificate_id}/observations")
    def add_manual_observation(
        certificate_id: int,
        payload: ManualObservationRequest,
        session: DbSession,
    ):
        observation = ReviewService(settings).add_manual_observation(
            session,
            certificate_id=certificate_id,
            product_id=payload.product_id,
            heat_id=payload.heat_id,
            field_path=payload.field_path,
            normalized_value=payload.normalized_value,
            raw_value=payload.raw_value,
            unit=payload.unit,
            person_name=payload.person_name,
            reason=payload.reason,
        )
        return ok({"observation_id": observation.id, "field_path": observation.field_path})

    def transition(run_id: int, target: ApprovalStatus, payload: ActorReason, session: Session):
        run = ReviewService(settings).transition_classification(
            session,
            run_id=run_id,
            target=target,
            person_name=payload.person_name,
            reason=payload.reason,
        )
        return ok({"classification_run_id": run.id, "approval_status": run.approval_status})

    @app.post(
        "/api/v1/classification-runs/{run_id}/approve",
        responses={
            200: {"model": Envelope, "description": "Ejecución de clasificación aprobada"},
            404: {"model": ErrorEnvelope, "description": "Ejecución no encontrada"},
            409: {"model": ErrorEnvelope, "description": "No se puede aprobar la ejecución"},
        },
    )
    def approve(run_id: int, payload: ActorReason, session: DbSession):
        return transition(run_id, ApprovalStatus.APPROVED, payload, session)

    @app.post("/api/v1/classification-runs/{run_id}/reject")
    def reject(run_id: int, payload: ActorReason, session: DbSession):
        return transition(run_id, ApprovalStatus.REJECTED, payload, session)

    @app.post(
        "/api/v1/classification-results/{result_id}/select",
        responses={
            200: {"model": CandidateSelectionEnvelope, "description": "Selección registrada correctamente"},
            404: {"model": ErrorEnvelope, "description": "Resultado o candidato no encontrado"},
            409: {"model": ErrorEnvelope, "description": "Conflicto en la selección del candidato"},
        },
    )
    def select_classification_candidate(
        result_id: int,
        payload: CandidateSelectionRequest,
        session: DbSession,
    ):
        selection = ReviewService(settings).select_classification_candidate(
            session,
            result_id=result_id,
            candidate_id=payload.candidate_id,
            person_name=payload.person_name,
            reason=payload.reason,
        )
        candidate = session.get(ClassificationCandidate, selection.candidate_id)
        assert candidate is not None
        return ok({
            "selection_id": selection.id,
            "classification_result_id": selection.classification_result_id,
            "candidate_id": selection.candidate_id,
            "fraction": candidate.fraction,
            "nico": candidate.nico,
            "person_name": selection.person_name,
            "reason": selection.reason,
            "workstation_name": selection.workstation_name,
            "created_at": selection.created_at.isoformat(),
        })

    @app.post("/api/v1/certificates/{certificate_id}/reclassify", status_code=status.HTTP_202_ACCEPTED)
    def reclassify_certificate(
        certificate_id: int,
        payload: ReclassificationRequest,
        session: DbSession,
    ):
        certificate = session.get(MillCertificate, certificate_id)
        if certificate is None:
            raise NotFoundError("Acta", certificate_id)
        job = Job(
            document_id=certificate.document_id,
            kind="reclassify",
            status="queued",
            payload_json={
                "certificate_id": certificate_id,
                "person_name": payload.person_name,
                "reason": payload.reason,
                "rule_set_id": payload.rule_set_id,
                "source_run_id": payload.source_run_id,
            },
        )
        session.add(job)
        session.flush()
        return ok({"certificate_id": certificate_id, "job_id": job.id}, status_code=202)

    @app.post(
        "/api/v1/certificates/{certificate_id}/reprocess",
        responses={
            200: {"model": ReprocessEnvelope, "description": "Reprocesamiento ejecutado o encolado"},
            400: {"model": ErrorEnvelope, "description": "Solicitud inválida"},
            404: {"model": ErrorEnvelope, "description": "Acta o documento no encontrado"},
        },
    )
    def reprocess_certificate(
        certificate_id: int,
        payload: ReprocessRequest,
        session: DbSession,
    ):
        result = DocumentQualityService(settings).reprocess_certificate(
            session,
            certificate_id=certificate_id,
            from_stage=payload.from_stage,  # type: ignore[arg-type]
            person_name=payload.person_name,
            reason=payload.reason,
        )
        return ok(result)


    @app.get("/api/v1/certificates/{certificate_id}/classification-runs")
    def list_classification_runs(certificate_id: int, session: DbSession):
        if session.get(MillCertificate, certificate_id) is None:
            raise NotFoundError("Acta", certificate_id)
        runs = session.scalars(
            select(ClassificationRun)
            .where(ClassificationRun.certificate_id == certificate_id)
            .order_by(ClassificationRun.id.desc())
        ).all()
        return ok([{
            "id": run.id,
            "rule_set_id": run.rule_set_id,
            "parent_run_id": run.parent_run_id,
            "approval_status": run.approval_status,
            "demo_notice": run.demo_notice,
            "created_at": run.created_at.isoformat(),
        } for run in runs])

    @app.get(
        "/api/v1/classification-runs/{run_id}",
        responses={
            200: {"model": Envelope, "description": "Detalle de la ejecución con candidatos y factores"},
            404: {"model": ErrorEnvelope, "description": "Ejecución no encontrada"},
        },
    )
    def classification_run_detail(run_id: int, session: DbSession):
        run = session.get(ClassificationRun, run_id)
        if run is None:
            raise NotFoundError("Ejecución de clasificación", run_id)
        results = session.scalars(
            select(ClassificationResult)
            .where(ClassificationResult.classification_run_id == run.id)
            .order_by(ClassificationResult.id)
        ).all()
        result_ids = [result.id for result in results]
        candidates = session.scalars(
            select(ClassificationCandidate)
            .where(ClassificationCandidate.classification_result_id.in_(result_ids))
            .order_by(ClassificationCandidate.classification_result_id, ClassificationCandidate.rank)
        ).all() if result_ids else []
        candidate_ids = [candidate.id for candidate in candidates]
        factors = session.scalars(
            select(CandidateFactor)
            .where(CandidateFactor.candidate_id.in_(candidate_ids))
            .order_by(CandidateFactor.candidate_id, CandidateFactor.sequence)
        ).all() if candidate_ids else []
        factor_ids = [factor.id for factor in factors]
        factor_evidence_links = session.scalars(
            select(EvidenceLink)
            .where(EvidenceLink.candidate_factor_id.in_(factor_ids))
            .order_by(EvidenceLink.candidate_factor_id, EvidenceLink.id)
        ).all() if factor_ids else []
        factor_links: dict[int, list[dict[str, Any]]] = {}
        for link in factor_evidence_links:
            assert link.candidate_factor_id is not None
            factor_links.setdefault(link.candidate_factor_id, []).append({
                "id": link.id,
                "source_type": link.source_type,
                "field_path": link.field_path,
                "observation_id": link.observation_id,
                "reference": link.source_reference_json,
                "detail_url": f"/api/v1/evidence/{link.id}",
            })
        factors_by_candidate: dict[int, list[dict[str, Any]]] = {}
        for factor in factors:
            factors_by_candidate.setdefault(factor.candidate_id, []).append(
                serialize_candidate_factor(factor, factor_links.get(factor.id, []))
            )
        candidates_by_result: dict[int, list[dict[str, Any]]] = {}
        for candidate in candidates:
            candidates_by_result.setdefault(candidate.classification_result_id, []).append({
                "id": candidate.id,
                "rank": candidate.rank,
                "fraction": candidate.fraction,
                "nico": candidate.nico,
                "description": candidate.description,
                "support_level": candidate.support_level,
                "details": candidate.details_json,
                "detail_url": f"/api/v1/classification-candidates/{candidate.id}",
                "factors": factors_by_candidate.get(candidate.id, []),
            })
        selections = session.scalars(
            select(ClassificationSelection)
            .where(ClassificationSelection.classification_result_id.in_(result_ids))
            .order_by(ClassificationSelection.classification_result_id, ClassificationSelection.id)
        ).all() if result_ids else []
        selections_by_result: dict[int, list[dict[str, Any]]] = {}
        for selection in selections:
            selections_by_result.setdefault(selection.classification_result_id, []).append({
                "id": selection.id,
                "candidate_id": selection.candidate_id,
                "supersedes_selection_id": selection.supersedes_selection_id,
                "person_name": selection.person_name,
                "reason": selection.reason,
                "workstation_name": selection.workstation_name,
                "created_at": selection.created_at.isoformat(),
            })
        current_selection_by_result: dict[int, dict[str, Any] | None] = {}
        for r_id in result_ids:
            r_sels = selections_by_result.get(r_id, [])
            superseded_ids = {s["supersedes_selection_id"] for s in r_sels if s["supersedes_selection_id"] is not None}
            active_sels = [s for s in r_sels if s["id"] not in superseded_ids]
            current_selection_by_result[r_id] = active_sels[-1] if active_sels else (r_sels[-1] if r_sels else None)
        steps = session.scalars(
            select(DecisionStep)
            .where(DecisionStep.classification_result_id.in_(result_ids))
            .order_by(DecisionStep.classification_result_id, DecisionStep.sequence)
        ).all() if result_ids else []
        step_ids = [step.id for step in steps]
        evidence_links = session.scalars(
            select(EvidenceLink)
            .where(EvidenceLink.decision_step_id.in_(step_ids))
            .order_by(EvidenceLink.decision_step_id, EvidenceLink.id)
        ).all() if step_ids else []
        links_by_step: dict[int, list[dict[str, Any]]] = {}
        for link in evidence_links:
            links_by_step.setdefault(link.decision_step_id, []).append({
                "id": link.id,
                "source_type": link.source_type,
                "field_path": link.field_path,
                "observation_id": link.observation_id,
                "reference": link.source_reference_json,
                "detail_url": f"/api/v1/evidence/{link.id}",
            })
        steps_by_result: dict[int, list[dict[str, Any]]] = {}
        for step in steps:
            steps_by_result.setdefault(step.classification_result_id, []).append({
                "id": step.id,
                "sequence": step.sequence,
                "rule_code": step.rule_code,
                "outcome": step.outcome,
                "inputs": step.input_json,
                "evidence": step.evidence_json,
                "evidence_links": links_by_step.get(step.id, []),
                "explanation": step.explanation,
            })
        return ok({
            "id": run.id,
            "certificate_id": run.certificate_id,
            "rule_set_id": run.rule_set_id,
            "parent_run_id": run.parent_run_id,
            "approval_status": run.approval_status,
            "input_snapshot": run.input_snapshot_json,
            "demo_notice": run.demo_notice,
            "results": [{
                "id": result.id,
                "product_id": result.product_id,
                "product_type": result.product_type,
                "fraction": result.fraction,
                "nico": result.nico,
                "description": result.description,
                "outcome": result.outcome,
                "details": result.details_json,
                "candidates": candidates_by_result.get(result.id, []),
                "current_selection": current_selection_by_result.get(result.id),
                "selections": selections_by_result.get(result.id, []),
                "steps": steps_by_result.get(result.id, []),
            } for result in results],
        })

    return app
