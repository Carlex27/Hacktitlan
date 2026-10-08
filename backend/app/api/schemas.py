from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


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


class CorrectionRequest(ActorReason):
    raw_value: Any | None = None
    normalized_value: Any | None = None
    unit: str | None = Field(default=None, max_length=50)


class ExportRequest(BaseModel):
    certificate_ids: list[int] = Field(default_factory=list, max_length=20_000)
    heat_ids: list[int] = Field(default_factory=list, max_length=20_000)
    classification_run_ids: list[int] = Field(default_factory=list, max_length=20_000)
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


class CandidateSelectionRequest(ActorReason):
    candidate_id: int = Field(ge=1)


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




