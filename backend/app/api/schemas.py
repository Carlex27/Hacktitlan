from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from backend.app.domain.enums import ApprovalStatus, ProcessingStatus


class CertificateDeletionRead(BaseModel):
    certificate_id: int
    document_id: int
    deleted: Literal[True]


class CertificateDeletionEnvelope(BaseModel):
    data: CertificateDeletionRead
    meta: dict[str, Any] = Field(default_factory=dict)
    error: None = None


class ActorReason(BaseModel):
    person_name: str = Field(min_length=2, max_length=200)
    reason: str = Field(min_length=3, max_length=4000)

    @field_validator("person_name", "reason")
    @classmethod
    def not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("El valor no puede estar vacío")
        return value


class RunDecisionRead(BaseModel):
    classification_run_id: int
    approval_status: ApprovalStatus


class RunDecisionEnvelope(BaseModel):
    data: RunDecisionRead
    meta: dict[str, Any] = Field(default_factory=dict)
    error: None = None


class ReclassificationRead(BaseModel):
    certificate_id: int
    job_id: int


class ReclassificationEnvelope(BaseModel):
    data: ReclassificationRead
    meta: dict[str, Any] = Field(default_factory=dict)
    error: None = None


class DocumentUploadRead(BaseModel):
    document_id: int
    certificate_id: int
    job_id: int | None
    duplicate: bool


class DocumentUploadEnvelope(BaseModel):
    data: DocumentUploadRead
    meta: dict[str, Any] = Field(default_factory=dict)
    error: None = None


class JobRead(BaseModel):
    id: int
    document_id: int | None
    kind: str
    status: ProcessingStatus
    progress: int = Field(ge=0, le=100)
    attempts: int
    max_attempts: int
    error_code: str | None
    error_message: str | None
    result: dict[str, Any] | None


class JobEnvelope(BaseModel):
    data: JobRead
    meta: dict[str, Any] = Field(default_factory=dict)
    error: None = None


class SpreadsheetRowRead(BaseModel):
    row: int
    cells: dict[str, Any]


class SpreadsheetSheetRead(BaseModel):
    sheet: str
    rows: list[SpreadsheetRowRead]


class SpreadsheetRead(BaseModel):
    document_id: int
    processing_status: str
    file_url: str
    sheets: list[SpreadsheetSheetRead] = Field(default_factory=list)
    specification_records: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    formula_policy: Literal["preserved_not_evaluated"] = "preserved_not_evaluated"


class SpreadsheetEnvelope(BaseModel):
    data: SpreadsheetRead
    meta: dict[str, Any] = Field(default_factory=dict)
    error: None = None


class CorrectionRequest(ActorReason):
    accept_verification: bool = False
    raw_value: Any | None = None
    normalized_value: Any | None = None
    unit: str | None = Field(default=None, max_length=50)


class FieldVerificationRead(BaseModel):
    status: Literal["matches", "discrepancy", "not_verifiable", "error"]
    model: str
    raw_value: str | None = None
    normalized_value: float | None = None
    unit: str | None = None
    page_number: int | None = None
    bbox: dict[str, float] | None = None
    source_id: str | None = None
    source_text: str | None = None
    header_id: str | None = None
    header_text: str | None = None
    header_bbox: dict[str, float] | None = None
    error_code: str | None = None


class CertificateObservationRead(BaseModel):
    id: int
    heat_id: int | None
    product_id: int | None
    field_path: str
    raw_value: Any | None
    normalized_value: Any | None
    unit: str | None
    confidence: float | None
    page_number: int | None
    bbox: Any | None
    source_text: str | None
    inherited: bool
    supersedes_id: int | None
    is_current: bool
    verification: FieldVerificationRead | None = None


class CertificateDetailRead(BaseModel):
    id: int
    document_id: int
    manufacturer: str | None
    certificate_no: str | None
    certificate_date: str | None
    uploaded_at: str
    revision_number: int
    previous_revision_id: int | None
    approval_status: ApprovalStatus
    standard: str | None
    product_name: str | None
    demo_notice: str
    heats: list[dict[str, Any]]
    products: list[dict[str, Any]]
    observations: list[CertificateObservationRead]
    chemical_compositions: list[dict[str, Any]]


class CertificateDetailEnvelope(BaseModel):
    data: CertificateDetailRead
    meta: dict[str, Any] = Field(default_factory=dict)
    error: None = None


class ExportRequest(BaseModel):
    certificate_ids: list[Annotated[int, Field(ge=1)]] = Field(default_factory=list, max_length=20_000)
    heat_ids: list[Annotated[int, Field(ge=1)]] = Field(default_factory=list, max_length=20_000)
    classification_run_ids: list[Annotated[int, Field(ge=1)]] = Field(default_factory=list, max_length=20_000)
    filters: dict[str, Any] = Field(default_factory=dict)
    official: bool = False
    person_name: str = Field(min_length=2, max_length=200)
    workstation_name: str | None = Field(default=None, max_length=200)

    @field_validator("person_name")
    @classmethod
    def person_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("La persona solicitante es obligatoria")
        return value

    @model_validator(mode="after")
    def scope_is_not_empty(self):
        if not self.certificate_ids and not self.heat_ids and not self.classification_run_ids:
            raise ValueError("Debe seleccionar al menos un acta, una colada o una ejecución")
        return self


class ArchiveRequest(ActorReason):
    archived: bool


class ReclassificationRequest(ActorReason):
    rule_set_id: int | None = Field(default=None, ge=1)
    source_run_id: int | None = Field(default=None, ge=1)


class CandidateSelectionRequest(ActorReason):
    candidate_id: int | None = Field(default=None, ge=1)
    fraction: str | None = Field(default=None, pattern=r"^[0-9]{8}$")
    nico: str | None = Field(default=None, pattern=r"^[0-9]{2}$")

    @model_validator(mode="after")
    def selection_source(self) -> CandidateSelectionRequest:
        if self.candidate_id is not None:
            if self.fraction is not None or self.nico is not None:
                raise ValueError("Enviar candidato o fracción y NICO manuales, no ambos")
        elif self.fraction is None or self.nico is None:
            raise ValueError("La captura manual requiere fracción de 8 dígitos y NICO de 2 dígitos")
        return self


class DeselectionRead(BaseModel):
    classification_result_id: int
    outcome: Literal["needs_review", "classified", "out_of_scope"]


class DeselectionEnvelope(BaseModel):
    data: DeselectionRead
    meta: dict[str, Any] = Field(default_factory=dict)
    error: dict[str, Any] | None = None


class ManualObservationRequest(ActorReason):
    product_id: int | None = Field(default=None, ge=1)
    heat_id: int | None = Field(default=None, ge=1)
    field_path: str = Field(min_length=1, max_length=500)
    raw_value: Any | None = None
    normalized_value: Any
    unit: str | None = Field(default=None, max_length=50)

    @model_validator(mode="after")
    def exactly_one_scope(self):
        if (self.product_id is None) == (self.heat_id is None):
            raise ValueError("Debe indicar exactamente product_id o heat_id")
        if self.normalized_value is None:
            raise ValueError("La captura manual requiere un valor normalizado")
        return self


class Envelope(BaseModel):
    data: Any | None = None
    meta: dict[str, Any] = Field(default_factory=dict)
    error: dict[str, Any] | None = None


class FactorEvidenceLink(BaseModel):
    id: int
    source_type: str
    field_path: str | None = None
    observation_id: int | None = None
    reference: dict[str, Any] = Field(default_factory=dict)
    detail_url: str


class RuleSourceReference(BaseModel):
    source_hash: str
    legal_status: str
    file_url: str
    page_number: int | None = None
    bbox: dict[str, float] | None = None
    source_text: str | None = None
    can_focus_region: bool
    fallback: str | None = None
    model_config = {"extra": "allow"}


class RuleSourceEvidenceRead(BaseModel):
    id: int
    decision_step_id: int | None = None
    candidate_factor_id: int | None = None
    source_type: Literal["rule_source"]
    reference: RuleSourceReference | dict[str, Any]


class ObservationEvidenceRead(BaseModel):
    id: int
    decision_step_id: int | None = None
    candidate_factor_id: int | None = None
    source_type: Literal["observation"]
    field_path: str | None = None
    observation: dict[str, Any]
    document: dict[str, Any]
    focus: dict[str, Any]


class EvidenceEnvelope(BaseModel):
    data: RuleSourceEvidenceRead | ObservationEvidenceRead
    meta: dict[str, Any] = Field(default_factory=dict)
    error: ErrorDetail | None = None


class CandidateFactorRead(BaseModel):
    id: int
    sequence: int
    rule_code: str
    outcome: str
    operator: str | None = None
    expected: dict[str, Any] = Field(default_factory=dict)
    observed: dict[str, Any] = Field(default_factory=dict)
    unit: str | None = None
    explanation: str
    required_for_selection: bool = True
    evidence_links: list[FactorEvidenceLink] = Field(default_factory=list)


class CandidateDetailRead(BaseModel):
    id: int
    classification_result_id: int
    rank: int
    fraction: str
    nico: str
    description: str
    support_level: str
    details: dict[str, Any] = Field(default_factory=dict)
    factors: list[CandidateFactorRead] = Field(default_factory=list)


class CandidateSelectionRead(BaseModel):
    selection_id: int
    classification_result_id: int
    candidate_id: int
    fraction: str
    nico: str
    person_name: str
    reason: str
    workstation_name: str
    created_at: str


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorEnvelope(BaseModel):
    data: Any | None = None
    meta: dict[str, Any] = Field(default_factory=dict)
    error: ErrorDetail


class CandidateDetailEnvelope(BaseModel):
    data: CandidateDetailRead
    meta: dict[str, Any] = Field(default_factory=dict)
    error: ErrorDetail | None = None


class CandidateSelectionEnvelope(BaseModel):
    data: CandidateSelectionRead
    meta: dict[str, Any] = Field(default_factory=dict)
    error: ErrorDetail | None = None


class QualityIssueItem(BaseModel):
    code: str
    category: str
    severity: str
    scope: str
    field_path: str
    message: str
    entity_identifier: str | None = None
    raw_value: Any | None = None
    normalized_value: Any | None = None
    confidence: float | None = None
    page_number: int | None = None
    bbox: dict[str, Any] | None = None


class DocumentQualityReportRead(BaseModel):
    certificate_id: int | None = None
    status: str
    quality_score: float
    product_family: str
    blocking_count: int
    warning_count: int
    provenance_summary: dict[str, int] = Field(default_factory=dict)
    issues: list[QualityIssueItem] = Field(default_factory=list)


class DocumentReviewSummaryIssue(BaseModel):
    code: str
    category: str
    severity: str
    field_path: str
    message: str


class DocumentReviewQueueItem(BaseModel):
    revision_number: int
    active_job_id: int | None = None
    can_reprocess: bool
    certificate_id: int
    document_id: int
    certificate_no: str | None = None
    manufacturer: str | None = None
    uploaded_at: str
    document_status: str
    approval_status: str
    quality_score: float
    blocking_issues_count: int
    warning_issues_count: int
    issues_summary: list[DocumentReviewSummaryIssue] = Field(default_factory=list)


class ReprocessRequest(ActorReason):
    from_stage: str = Field(pattern="^(extraction|normalization|classification)$")


class DocumentQualityReportEnvelope(BaseModel):
    data: DocumentQualityReportRead
    meta: dict[str, Any] = Field(default_factory=dict)
    error: ErrorDetail | None = None


class DocumentReviewQueueEnvelope(BaseModel):
    data: list[DocumentReviewQueueItem]
    meta: dict[str, Any] = Field(default_factory=dict)
    error: ErrorDetail | None = None


class ReprocessRead(BaseModel):
    certificate_id: int
    job_id: int | None = None
    stage: str
    status: str
    quality_report: DocumentQualityReportRead | None = None


class ReprocessEnvelope(BaseModel):
    data: ReprocessRead
    meta: dict[str, Any] = Field(default_factory=dict)
    error: ErrorDetail | None = None
