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
    UNKNOWN = "unknown"
    CONFLICT = "conflict"


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
    high_speed_steel: bool | None = None
    tool_steel: bool | None = None
    grain_oriented: bool | None = None
    magnetic_silicon: bool | None = None
    stainless_series: str | None = None
    rolled_four_faces: bool | None = None
    clad: bool | None = None
    temper: str | None = None
    magnetic_loss_w_per_kg: Decimal | None = None
    magnetic_induction_tesla: Decimal | None = None
    secondary_reduction_ratio: Decimal | None = None
    can_body_end_use: bool | None = None
    deep_drawing_class: str | None = None
    cladding_weight_percentage: Decimal | None = None


@dataclass(frozen=True)
class Decision:
    rule_code: str
    outcome: StepOutcome
    explanation: str
    inputs: dict[str, Any] = field(default_factory=dict)
    evidence: list[Any] = field(default_factory=list)
    evidence_fields: tuple[str, ...] = ()


@dataclass(frozen=True)
class ClassificationCandidate:
    rank: int
    fraction: str
    nico: str
    description: str | None
    support_level: str
    missing_fields: tuple[str, ...] = ()
    conflicts: tuple[str, ...] = ()
    factors: tuple[CandidateFactor, ...] = ()


@dataclass(frozen=True)
class CandidateFactor:
    sequence: int
    rule_code: str
    outcome: StepOutcome
    explanation: str
    operator: str | None = None
    expected: dict[str, Any] = field(default_factory=dict)
    observed: dict[str, Any] = field(default_factory=dict)
    unit: str | None = None
    evidence_fields: tuple[str, ...] = ()
    required_for_selection: bool = True


@dataclass(frozen=True)
class DiscardedCandidate:
    fraction: str
    nico: str
    reason_code: str
    explanation: str


@dataclass(frozen=True)
class ClassificationDecision:
    outcome: ClassificationOutcome
    product_type: str | None
    fraction: str | None
    nico: str | None
    description: str | None
    missing_fields: tuple[str, ...]
    candidates: tuple[str, ...]
    ranked_candidates: tuple[ClassificationCandidate, ...]
    discarded_candidates: tuple[DiscardedCandidate, ...]
    steps: tuple[Decision, ...]
