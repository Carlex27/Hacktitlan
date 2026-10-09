"""Permanent removal of test certificates and their owned artifacts."""

from pathlib import Path
from uuid import uuid4

from sqlalchemy import delete, select, text, update
from sqlalchemy.orm import Session

from backend.app.config import Settings
from backend.app.domain.errors import ApplicationError, ConflictError, NotFoundError
from backend.app.infrastructure.database.models import (
    ApprovalEvent, CandidateFactor, ChemicalComposition, ClassificationCandidate,
    ClassificationResult, ClassificationRun, ClassificationSelection, Correction,
    DecisionStep, Document, EvidenceLink, Export, ExtractionRun, Heat, Job,
    MillCertificate, Observation, Product, StoredFile,
)
from backend.app.infrastructure.files import FileStorage


def delete_certificate(session: Session, settings: Settings, storage: FileStorage,
                       certificate_id: int) -> dict[str, int | bool]:
    if settings.environment not in {"development", "test"}:
        raise ApplicationError("certificate_deletion_disabled",
                               "La eliminación sólo está habilitada en desarrollo y pruebas",
                               status_code=403)

    # shortcut: serializa escrituras de pruebas; usar bloqueos por acta para uso productivo.
    session.execute(text(
        "LOCK TABLE jobs, documents, mill_certificates, stored_files, exports, "
        "extraction_runs, heats, products, observations, chemical_compositions, "
        "classification_runs, classification_results, classification_candidates, "
        "classification_selections, candidate_factors, decision_steps, evidence_links, "
        "corrections, approval_events IN SHARE ROW EXCLUSIVE MODE"
    ))
    certificate = session.get(MillCertificate, certificate_id)
    if certificate is None:
        raise NotFoundError("Acta", certificate_id)
    document = session.get(Document, certificate.document_id)
    assert document is not None
    document_id = document.id
    heats = list(session.scalars(select(Heat.id).where(Heat.certificate_id == certificate_id)))
    products = list(session.scalars(select(Product.id).where(Product.certificate_id == certificate_id)))
    runs = list(session.scalars(select(ClassificationRun.id).where(
        ClassificationRun.certificate_id == certificate_id)))
    results = list(session.scalars(select(ClassificationResult.id).where(
        ClassificationResult.classification_run_id.in_(runs))))
    candidates = list(session.scalars(select(ClassificationCandidate.id).where(
        ClassificationCandidate.classification_result_id.in_(results))))
    factors = list(session.scalars(select(CandidateFactor.id).where(CandidateFactor.candidate_id.in_(candidates))))
    steps = list(session.scalars(select(DecisionStep.id).where(DecisionStep.classification_result_id.in_(results))))
    observations = list(session.scalars(select(Observation.id).where(Observation.certificate_id == certificate_id)))
    exports = [item for item in session.scalars(select(Export)) if (
        item.classification_run_id in runs
        or certificate_id in (item.scope_json.get("certificate_ids") or [])
        or set(heats).intersection(item.scope_json.get("heat_ids") or [])
        or set(runs).intersection(item.scope_json.get("classification_run_ids") or [])
    )]
    export_ids = [item.id for item in exports]
    jobs = [job for job in session.scalars(select(Job)) if (
        job.document_id == document_id or job.payload_json.get("export_id") in export_ids
    )]
    if any(job.status == "running" for job in jobs) or any(item.status == "running" for item in exports):
        raise ConflictError("certificate_in_use", "El acta tiene trabajos en ejecución; espera a que terminen")

    file_ids = {document.stored_file_id} | {item.stored_file_id for item in exports if item.stored_file_id}
    moved: list[tuple[Path, Path]] = []
    try:
        session.execute(delete(EvidenceLink).where(
            EvidenceLink.decision_step_id.in_(steps)
            | EvidenceLink.candidate_factor_id.in_(factors)
            | EvidenceLink.observation_id.in_(observations)))
        session.execute(update(ClassificationSelection).where(
            ClassificationSelection.classification_result_id.in_(results)).values(supersedes_selection_id=None))
        for model, condition in (
            (ClassificationSelection, ClassificationSelection.classification_result_id.in_(results)),
            (CandidateFactor, CandidateFactor.id.in_(factors)),
            (ClassificationCandidate, ClassificationCandidate.id.in_(candidates)),
            (DecisionStep, DecisionStep.id.in_(steps)),
            (ApprovalEvent, ApprovalEvent.classification_run_id.in_(runs)),
            (Export, Export.id.in_(export_ids)),
            (ClassificationResult, ClassificationResult.id.in_(results)),
        ):
            session.execute(delete(model).where(condition))
        session.execute(update(ClassificationRun).where(ClassificationRun.id.in_(runs)).values(parent_run_id=None))
        session.execute(delete(ClassificationRun).where(ClassificationRun.id.in_(runs)))
        session.execute(delete(Correction).where(Correction.certificate_id == certificate_id))
        session.execute(update(Observation).where(Observation.id.in_(observations)).values(supersedes_id=None))
        session.execute(delete(Observation).where(Observation.id.in_(observations)))
        session.execute(delete(ChemicalComposition).where(
            ChemicalComposition.heat_id.in_(heats) | ChemicalComposition.product_id.in_(products)))
        session.execute(delete(Product).where(Product.id.in_(products)))
        session.execute(delete(Heat).where(Heat.id.in_(heats)))
        # Las otras revisiones permanecen como actas independientes.
        session.execute(update(MillCertificate).where(
            MillCertificate.previous_revision_id == certificate_id).values(previous_revision_id=None))
        session.execute(delete(MillCertificate).where(MillCertificate.id == certificate_id))
        session.execute(delete(ExtractionRun).where(ExtractionRun.document_id == document_id))
        session.execute(delete(Job).where(Job.id.in_([job.id for job in jobs])))
        session.execute(delete(Document).where(Document.id == document_id))
        for file_id in file_ids:
            if session.scalar(select(Document.id).where(Document.stored_file_id == file_id).limit(1)):
                continue
            if session.scalar(select(Export.id).where(Export.stored_file_id == file_id).limit(1)):
                continue
            stored = session.get(StoredFile, file_id)
            assert stored is not None
            try:
                source = storage.resolve(stored.relative_path)
            except ApplicationError as exc:
                if exc.code != "stored_file_missing":
                    raise
            else:
                temporary = storage.temp_root / f"delete-{uuid4().hex}"
                source.replace(temporary)
                moved.append((source, temporary))
            session.execute(delete(StoredFile).where(StoredFile.id == file_id))
        session.commit()
    except Exception:
        session.rollback()
        for source, temporary in reversed(moved):
            temporary.replace(source)
        raise
    for _, temporary in moved:
        temporary.unlink(missing_ok=True)
    return {"certificate_id": certificate_id, "document_id": document_id, "deleted": True}
