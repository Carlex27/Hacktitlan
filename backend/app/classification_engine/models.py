from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum
from typing import Any


class ClassificationOutcome(StrEnum):
    CLASSIFIED = "classified"
    NEEDS_REVIEW = "needs_review"
    OUT_OF_SCOPE = "out_of_scope"


class StepOutcome(StrEnum):
    MATCHED = "matched"
    NOT_MATCHED = "not_matched"
    MISSING = "missing"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True)
class ProductFacts:
    product_id: int | str
    form: str | None
    coiled: bool | None
    rolling: str | None
    width_mm: Decimal | None
    thickness_mm: Decimal | None
    composition_pct: dict[str, Decimal | None]
    coated: bool | None = None
    coating_metal: str | None = None
    coating_process: str | None = None
    coating_both_sides: bool | None = None
    yield_strength_mpa: Decimal | None = None
    pickled: bool | None = None
    pattern_in_relief: bool | None = None
    porcelain_exposed_parts: bool | None = None
    pipeline_steel: bool | None = None


@dataclass(frozen=True)
class Decision:
    rule_code: str
    outcome: StepOutcome
    explanation: str
    inputs: dict[str, Any] = field(default_factory=dict)
    evidence: list[Any] = field(default_factory=list)


@dataclass(frozen=True)
class ClassificationDecision:
    outcome: ClassificationOutcome
    product_type: str | None
    fraction: str | None
    nico: str | None
    description: str | None
    missing_fields: tuple[str, ...]
    candidates: tuple[str, ...]
    steps: tuple[Decision, ...]

