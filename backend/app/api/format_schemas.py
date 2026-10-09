"""Public draft-format, prepared-layout and preview contracts."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator

from backend.app.api.schemas import ActorReason
from backend.app.certificate_parser.templates import TemplateConfiguration, TemplatePreview
from backend.app.domain.document import DocumentLayout
from backend.app.domain.enums import ProcessingStatus


class FormatCreate(ActorReason):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=1000)

    @field_validator("name")
    @classmethod
    def nonblank_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("El nombre no puede estar vacío")
        return value.strip()


class VersionCreate(ActorReason):
    model_config = ConfigDict(extra="forbid")
    configuration: TemplateConfiguration


class VersionEdit(VersionCreate):
    expected_revision: int = Field(ge=1, strict=True)


class PreviewRequest(ActorReason):
    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=1, strict=True)
    layout_id: int = Field(ge=1, strict=True)


class PreviewRevision(ActorReason):
    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=1, strict=True)


class FormatRead(BaseModel):
    id: int
    name: str
    description: str


class VersionRead(BaseModel):
    id: int
    format_id: int
    version_number: int
    revision: int
    status: Literal["draft", "active", "retired"]
    configuration: TemplateConfiguration
    configuration_sha256: str
    person_name: str
    reason: str
    updated_at: datetime
    lifecycle: list[dict[str, JsonValue]] = Field(default_factory=list)


class FormatDetail(FormatRead):
    versions: list[VersionRead]


class LayoutRead(BaseModel):
    id: int
    document_id: int
    document_sha256: str
    document: DocumentLayout


class PreviewTestRead(BaseModel):
    id: int
    version_id: int
    document_id: int
    layout_id: int
    job_id: int | None
    revision: int
    configuration_sha256: str
    extractor_sha256: str
    status: ProcessingStatus
    result: TemplatePreview | None
    current_revision: bool
    reviewed_by: str | None = None
    review_reason: str | None = None


class FormatJobRead(BaseModel):
    job_id: int


class FormatEnvelope[T](BaseModel):
    data: T
    meta: dict[str, JsonValue] = Field(default_factory=dict)
    error: None = None
