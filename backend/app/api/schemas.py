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
    official: bool = False
    person_name: str = Field(min_length=2, max_length=200)

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

