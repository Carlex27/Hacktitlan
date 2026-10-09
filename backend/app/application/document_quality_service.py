"""Application service for document quality validation, review queue, and reprocessing."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Literal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, aliased, joinedload

from backend.app.config import Settings, get_settings
from backend.app.domain.document_quality import (
    DocumentQualityReport,
    validate_document_quality,
)
from backend.app.domain.enums import ApprovalStatus, JobKind, ProcessingStatus
from backend.app.domain.errors import ApplicationError, NotFoundError
from backend.app.infrastructure.database.models import (
    ChemicalComposition,
    Document,
    Heat,
    Job,
    Manufacturer,
    MillCertificate,
    Observation,
    Product,
    StoredFile,
)

logger = logging.getLogger(__name__)


class DocumentQualityService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def evaluate_certificate(
        self,
        session: Session,
        certificate_id: int,
    ) -> DocumentQualityReport:
        certificate = session.get(MillCertificate, certificate_id)
        if certificate is None:
            raise NotFoundError("Acta", certificate_id)

        document = session.get(Document, certificate.document_id)
        manufacturer = (
            session.get(Manufacturer, certificate.manufacturer_id)
            if certificate.manufacturer_id
            else None
        )

        heats = session.scalars(
            select(Heat)
            .where(Heat.certificate_id == certificate.id)
            .order_by(Heat.id)
        ).all()
        products = session.scalars(
            select(Product)
            .where(Product.certificate_id == certificate.id)
            .order_by(Product.id)
        ).all()
        observations = session.scalars(
            select(Observation)
            .where(
                Observation.certificate_id == certificate.id,
                Observation.is_current.is_(True),
            )
            .order_by(Observation.id)
        ).all()

        heat_ids = [h.id for h in heats]
        product_ids = [p.id for p in products]
        compositions = session.scalars(
            select(ChemicalComposition)
            .where(
                (ChemicalComposition.heat_id.in_(heat_ids))
                | (ChemicalComposition.product_id.in_(product_ids))
            )
            .order_by(ChemicalComposition.id)
        ).all() if (heat_ids or product_ids) else []

        doc_metadata = {
            "certificate_no": certificate.certificate_no,
            "standard": certificate.standard,
            "supplier": manufacturer.name if manufacturer else None,
            "product_name": certificate.product_name,
            "certificate_date": certificate.certificate_date,
            **(document.metadata_json if document else {}),
        }

        prods_dict = [
            {
                "id": p.id,
                "product_identifier": p.product_identifier,
                "heat_id": p.heat_id,
                "coiled": p.coiled,
                "form": p.form,
                "rolling": p.rolling,
                "thickness_mm": p.thickness_mm,
                "width_mm": p.width_mm,
                "length_m": p.length_m,
                "weight_kg": p.weight_kg,
            }
            for p in products
        ]
        heats_dict = [
            {
                "id": h.id,
                "heat_no": h.heat_no,
                "standard": h.standard,
                "grade": h.grade,
            }
            for h in heats
        ]
        obs_dict = [
            {
                "id": o.id,
                "product_id": o.product_id,
                "heat_id": o.heat_id,
                "field_path": o.field_path,
                "raw_value": o.raw_value_json,
                "normalized_value": o.normalized_value_json,
                "unit": o.unit,
                "confidence": o.confidence,
                "page_number": o.page_number,
                "bbox": o.bbox_json,
                "source_text": o.source_text,
                "inherited": o.inherited,
            }
            for o in observations
        ]
        comp_dict = [
            {
                "id": c.id,
                "product_id": c.product_id,
                "heat_id": c.heat_id,
                "element": c.element,
                "raw_value": c.raw_value_json,
                "percentage": c.percentage,
                "inherited": c.inherited,
            }
            for c in compositions
        ]

        prods_by_id = {p["id"]: p for p in prods_dict}
        comps_by_key = {(c["product_id"], c["heat_id"], c["element"]): c for c in comp_dict}

        for o in observations:
            if o.product_id and o.product_id in prods_by_id:
                p_item = prods_by_id[o.product_id]
                if o.field_path in ("thickness_mm", "width_mm", "length_m", "weight_kg"):
                    if o.normalized_value_json is not None:
                        try:
                            p_item[o.field_path] = Decimal(str(o.normalized_value_json))
                        except Exception:
                            p_item[o.field_path] = o.normalized_value_json
                elif o.field_path in ("form", "rolling", "coiled"):
                    p_item[o.field_path] = o.normalized_value_json

            if o.field_path.startswith("composition_pct."):
                elem = o.field_path.split(".", 1)[1]
                key = (o.product_id, o.heat_id, elem)
                if key in comps_by_key:
                    try:
                        comps_by_key[key]["percentage"] = (
                            Decimal(str(o.normalized_value_json))
                            if o.normalized_value_json is not None
                            else None
                        )
                    except Exception:
                        comps_by_key[key]["percentage"] = o.normalized_value_json
                else:
                    try:
                        p_val = (
                            Decimal(str(o.normalized_value_json))
                            if o.normalized_value_json is not None
                            else None
                        )
                    except Exception:
                        p_val = o.normalized_value_json
                    new_c = {
                        "id": None,
                        "product_id": o.product_id,
                        "heat_id": o.heat_id,
                        "element": elem,
                        "raw_value": o.raw_value_json,
                        "percentage": p_val,
                        "inherited": o.inherited,
                    }
                    comp_dict.append(new_c)
                    comps_by_key[key] = new_c

        report = validate_document_quality(
            certificate_id=certificate.id,
            document_metadata=doc_metadata,
            products=prods_dict,
            heats=heats_dict,
            observations=obs_dict,
            compositions=comp_dict,
        )

        # Update document quality report cache in document metadata if available
        if document:
            meta = dict(document.metadata_json or {})
            meta["quality_report"] = report.as_dict()
            document.metadata_json = meta

        return report

    def get_review_queue(
        self,
        session: Session,
        *,
        limit: int = 50,
        status_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve certificates in document review queue with summarized quality issues."""
        query = (
            select(MillCertificate, Document, Manufacturer)
            .options(joinedload(Document.stored_file))
            .join(Document, MillCertificate.document_id == Document.id)
            .outerjoin(Manufacturer, MillCertificate.manufacturer_id == Manufacturer.id)
            .where(MillCertificate.approval_status != ApprovalStatus.APPROVED.value)
            .order_by(MillCertificate.id.desc())
        )
        revision_document = aliased(Document)
        latest_ids = (
            select(func.max(MillCertificate.id))
            .join(revision_document, MillCertificate.document_id == revision_document.id)
            .group_by(revision_document.stored_file_id)
        )
        query = query.where(MillCertificate.id.in_(latest_ids))
        if status_filter:
            query = query.where(MillCertificate.approval_status == status_filter)

        # shortcut: recalculates non-approved acts; persist indexed quality status before Hito 7 volume tests.
        rows = session.execute(query).all()
        results: list[dict[str, Any]] = []

        for cert, doc, mfr in rows:
            active_job = session.scalar(
                select(Job).join(Document, Job.document_id == Document.id).where(
                    Document.stored_file_id == doc.stored_file_id,
                    Job.kind == JobKind.EXTRACT_DOCUMENT.value,
                    Job.status.in_((ProcessingStatus.QUEUED.value, ProcessingStatus.RUNNING.value)),
                ).order_by(Job.id.desc()).limit(1)
            )
            report = self.evaluate_certificate(session, cert.id)
            if report.blocking_count == 0 and (
                doc.processing_status != ProcessingStatus.NEEDS_REVIEW.value
                and cert.approval_status != ApprovalStatus.NEEDS_REVIEW.value
            ):
                continue
            results.append({
                "certificate_id": cert.id,
                "document_id": doc.id,
                "source_file_name": doc.stored_file.original_name,
                "certificate_no": cert.certificate_no,
                "manufacturer": mfr.name if mfr else None,
                "uploaded_at": cert.uploaded_at.isoformat(),
                "document_status": doc.processing_status,
                "approval_status": cert.approval_status,
                "revision_number": cert.revision_number,
                "active_job_id": active_job.id if active_job else None,
                "can_reprocess": active_job is None,
                "quality_score": report.quality_score,
                "blocking_issues_count": report.blocking_count,
                "warning_issues_count": report.warning_count,
                "issues_summary": [
                    {
                        "code": issue.code,
                        "category": issue.category.value,
                        "severity": issue.severity.value,
                        "field_path": issue.field_path,
                        "message": issue.message,
                    }
                    for issue in report.issues[:5]
                ],
            })
            if len(results) >= limit:
                break

        return results

    def reprocess_certificate(
        self,
        session: Session,
        *,
        certificate_id: int,
        from_stage: Literal["extraction", "normalization", "classification"],
        person_name: str,
        reason: str,
    ) -> dict[str, Any]:
        """Trigger reprocessing from specified stage while preserving immutable historical events."""
        person_name = person_name.strip()
        reason = reason.strip()
        if not person_name or not reason:
            raise ApplicationError(
                "audit_fields_required",
                "La persona y el motivo son obligatorios para reprocesar",
            )

        certificate = session.get(MillCertificate, certificate_id)
        if certificate is None:
            raise NotFoundError("Acta", certificate_id)
        document = session.get(Document, certificate.document_id)
        if document is None:
            raise NotFoundError("Documento", certificate.document_id)
        if from_stage == "extraction":
            # Serialize requests for every revision of the same PDF, including sibling revisions.
            session.scalar(select(StoredFile).where(
                StoredFile.id == document.stored_file_id
            ).with_for_update())
            active_job = session.scalar(
                select(Job).join(Document, Job.document_id == Document.id).where(
                    Document.stored_file_id == document.stored_file_id,
                    Job.kind == JobKind.EXTRACT_DOCUMENT.value,
                    Job.status.in_((ProcessingStatus.QUEUED.value, ProcessingStatus.RUNNING.value)),
                ).order_by(Job.id.desc()).limit(1)
            )
            if active_job:
                raise ApplicationError(
                    "reprocess_in_progress", "Este PDF ya tiene una extracción en curso",
                    status_code=409, details={"job_id": active_job.id},
                )
            certificate_id = session.scalar(
                select(MillCertificate.id).join(Document).where(
                    Document.stored_file_id == document.stored_file_id
                ).order_by(MillCertificate.id.desc()).limit(1)
            )
        certificate = session.scalar(
            select(MillCertificate)
            .where(MillCertificate.id == certificate_id)
            .with_for_update()
        )
        if certificate is None:
            raise NotFoundError("Acta", certificate_id)

        document = session.get(Document, certificate.document_id)
        if document is None:
            raise NotFoundError("Documento", certificate.document_id)

        if from_stage == "extraction":
            metadata = dict(document.metadata_json or {})
            metadata.pop("quality_report", None)
            revision_document = Document(
                stored_file_id=document.stored_file_id,
                processing_status=ProcessingStatus.QUEUED.value,
                page_count=document.page_count,
                language=document.language,
                metadata_json=metadata,
            )
            session.add(revision_document)
            session.flush()
            revision = MillCertificate(
                document_id=revision_document.id,
                manufacturer_id=certificate.manufacturer_id,
                certificate_no=certificate.certificate_no,
                certificate_date=certificate.certificate_date,
                revision_number=certificate.revision_number + 1,
                previous_revision_id=certificate.id,
                approval_status=ApprovalStatus.NEEDS_REVIEW.value,
                standard=certificate.standard,
                product_name=certificate.product_name,
                demo_notice=certificate.demo_notice,
            )
            session.add(revision)
            session.flush()
            job = Job(
                document_id=revision_document.id,
                kind=JobKind.EXTRACT_DOCUMENT.value,
                status=ProcessingStatus.QUEUED.value,
                payload_json={
                    "certificate_id": revision.id,
                    "reprocess_stage": "extraction",
                    "person_name": person_name,
                    "reason": reason,
                    "workstation_name": self.settings.workstation_name,
                },
            )
            session.add(job)
            session.flush()
            return {
                "certificate_id": revision.id,
                "job_id": job.id,
                "stage": "extraction",
                "status": "queued",
            }

        elif from_stage == "normalization":
            # Re-evaluate document quality and current observations
            report = self.evaluate_certificate(session, certificate.id)
            if report.blocking_count == 0:
                certificate.approval_status = ApprovalStatus.DRAFT.value
                document.processing_status = ProcessingStatus.SUCCEEDED.value
            else:
                certificate.approval_status = ApprovalStatus.NEEDS_REVIEW.value
                document.processing_status = ProcessingStatus.NEEDS_REVIEW.value

            now = datetime.now(timezone.utc)
            audit_job = Job(
                document_id=document.id,
                kind=JobKind.NORMALIZE_DOCUMENT.value,
                status=ProcessingStatus.SUCCEEDED.value,
                progress=100,
                started_at=now,
                finished_at=now,
                payload_json={
                    "certificate_id": certificate.id,
                    "person_name": person_name,
                    "reason": reason,
                    "workstation_name": self.settings.workstation_name,
                    "reprocess_stage": "normalization",
                },
                result_json={"quality_report": report.as_dict()},
            )
            session.add(audit_job)
            session.flush()

            return {
                "certificate_id": certificate.id,
                "job_id": audit_job.id,
                "stage": "normalization",
                "status": "evaluated",
                "quality_report": report.as_dict(),
            }

        elif from_stage == "classification":
            # Enqueue reclassification job
            job = Job(
                document_id=document.id,
                kind=JobKind.RECLASSIFY.value,
                status=ProcessingStatus.QUEUED.value,
                payload_json={
                    "certificate_id": certificate.id,
                    "person_name": person_name,
                    "reason": reason,
                    "reprocess_stage": "classification",
                },
            )
            session.add(job)
            session.flush()
            return {
                "certificate_id": certificate.id,
                "job_id": job.id,
                "stage": "classification",
                "status": "queued",
            }

        else:
            raise ApplicationError(
                "invalid_reprocess_stage",
                f"Etapa de reprocesamiento '{from_stage}' no válida",
            )
