from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import BigInteger, Boolean, CheckConstraint, Date, ForeignKey, Identity, Index, Integer, JSON, String, Text, UniqueConstraint, event, inspect, select
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.domain.enums import ApprovalStatus, RuleSetStatus
from backend.app.infrastructure.database.models.common import TimestampMixin
from backend.app.infrastructure.database.models.core import MillCertificate, Observation, Product
from backend.app.infrastructure.database.session import Base


class RuleSet(TimestampMixin, Base):
    __tablename__ = "rule_sets"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    version: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default=RuleSetStatus.DRAFT.value)
    source_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    valid_from: Mapped[date | None] = mapped_column(Date)
    valid_to: Mapped[date | None] = mapped_column(Date)
    manifest_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    __table_args__ = (
        UniqueConstraint("name", "version", name="uq_rule_set_name_version"),
        CheckConstraint("status IN ('draft','approved','retired')", name="valid_status"),
    )


@event.listens_for(RuleSet, "before_update")
def prevent_immutable_rule_set_update(mapper, connection, target: RuleSet) -> None:
    from backend.app.classification_engine.versioning import validate_rule_set_immutability

    old_status = connection.execute(
        select(RuleSet.status).where(RuleSet.id == target.id)
    ).scalar_one()
    state = inspect(target)
    for field in ("name", "version", "source_hash", "valid_from", "valid_to", "manifest_json"):
        if state.attrs[field].history.has_changes():
            validate_rule_set_immutability(old_status, field)


class ClassificationRun(TimestampMixin, Base):
    __tablename__ = "classification_runs"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    certificate_id: Mapped[int] = mapped_column(
        ForeignKey("mill_certificates.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    rule_set_id: Mapped[int] = mapped_column(
        ForeignKey("rule_sets.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    parent_run_id: Mapped[int | None] = mapped_column(
        ForeignKey("classification_runs.id", ondelete="RESTRICT"), index=True
    )
    approval_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default=ApprovalStatus.DRAFT.value, index=True
    )
    input_snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    demo_notice: Mapped[str] = mapped_column(String(200), nullable=False)

    certificate: Mapped[MillCertificate] = relationship()
    rule_set: Mapped[RuleSet] = relationship()
    parent_run: Mapped[ClassificationRun | None] = relationship(remote_side="ClassificationRun.id")

    __table_args__ = (
        CheckConstraint(
            "approval_status IN ('draft','needs_review','approved','rejected')",
            name="valid_approval_status",
        ),
        Index("ix_classification_certificate_created", "certificate_id", "created_at"),
    )


class ClassificationResult(TimestampMixin, Base):
    __tablename__ = "classification_results"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    classification_run_id: Mapped[int] = mapped_column(
        ForeignKey("classification_runs.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    product_type: Mapped[str | None] = mapped_column(String(200))
    fraction: Mapped[str | None] = mapped_column(String(8), index=True)
    nico: Mapped[str | None] = mapped_column(String(2), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    outcome: Mapped[str] = mapped_column(String(30), nullable=False)
    details_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    classification_run: Mapped[ClassificationRun] = relationship()
    product: Mapped[Product] = relationship()

    __table_args__ = (
        UniqueConstraint(
            "classification_run_id", "product_id", name="uq_classification_run_product"
        ),
        CheckConstraint(
            "fraction IS NULL OR fraction ~ '^[0-9]{8}$'", name="fraction_format"
        ),
        CheckConstraint("nico IS NULL OR nico ~ '^[0-9]{2}$'", name="nico_format"),
        CheckConstraint(
            "outcome IN ('classified','needs_review','out_of_scope')",
            name="valid_outcome",
        ),
    )


class ClassificationCandidate(TimestampMixin, Base):
    __tablename__ = "classification_candidates"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    classification_result_id: Mapped[int] = mapped_column(
        ForeignKey("classification_results.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    fraction: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    nico: Mapped[str] = mapped_column(String(2), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    support_level: Mapped[str] = mapped_column(String(30), nullable=False)
    details_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    classification_result: Mapped[ClassificationResult] = relationship()

    __table_args__ = (
        UniqueConstraint(
            "classification_result_id", "rank", name="uq_candidate_result_rank"
        ),
        UniqueConstraint(
            "classification_result_id", "fraction", "nico",
            name="uq_candidate_result_code",
        ),
        CheckConstraint("rank BETWEEN 1 AND 3", name="candidate_rank_range"),
        CheckConstraint("fraction ~ '^[0-9]{8}$'", name="candidate_fraction_format"),
        CheckConstraint("nico ~ '^[0-9]{2}$'", name="candidate_nico_format"),
        CheckConstraint(
            "support_level IN ('fully_supported','conditional')",
            name="candidate_support_level",
        ),
    )


class ClassificationSelection(TimestampMixin, Base):
    __tablename__ = "classification_selections"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    classification_result_id: Mapped[int] = mapped_column(
        ForeignKey("classification_results.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("classification_candidates.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    supersedes_selection_id: Mapped[int | None] = mapped_column(
        ForeignKey("classification_selections.id", ondelete="RESTRICT"), index=True
    )
    person_name: Mapped[str] = mapped_column(String(200), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    workstation_name: Mapped[str] = mapped_column(String(200), nullable=False)

    classification_result: Mapped[ClassificationResult] = relationship()
    candidate: Mapped[ClassificationCandidate] = relationship()
    supersedes_selection: Mapped[ClassificationSelection | None] = relationship(
        remote_side="ClassificationSelection.id"
    )


class CandidateFactor(TimestampMixin, Base):
    __tablename__ = "candidate_factors"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("classification_candidates.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    rule_code: Mapped[str] = mapped_column(String(200), nullable=False)
    outcome: Mapped[str] = mapped_column(String(30), nullable=False)
    operator: Mapped[str | None] = mapped_column(String(100))
    expected_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    observed_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    unit: Mapped[str | None] = mapped_column(String(50))
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    required_for_selection: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    candidate: Mapped[ClassificationCandidate] = relationship()

    __table_args__ = (
        UniqueConstraint("candidate_id", "sequence", name="uq_factor_candidate_sequence"),
        CheckConstraint("sequence >= 1", name="candidate_factor_sequence_positive"),
        CheckConstraint(
            "outcome IN ('matched','not_matched','missing','ambiguous','unknown','conflict')",
            name="candidate_factor_outcome",
        ),
    )


class DecisionStep(TimestampMixin, Base):
    __tablename__ = "decision_steps"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    classification_result_id: Mapped[int] = mapped_column(
        ForeignKey("classification_results.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    rule_code: Mapped[str] = mapped_column(String(200), nullable=False)
    outcome: Mapped[str] = mapped_column(String(50), nullable=False)
    input_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    evidence_json: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    explanation: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        UniqueConstraint(
            "classification_result_id", "sequence", name="uq_decision_result_sequence"
        ),
        CheckConstraint("sequence >= 1", name="sequence_positive"),
    )


class EvidenceLink(TimestampMixin, Base):
    __tablename__ = "evidence_links"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    decision_step_id: Mapped[int | None] = mapped_column(
        ForeignKey("decision_steps.id", ondelete="RESTRICT"), index=True
    )
    candidate_factor_id: Mapped[int | None] = mapped_column(
        ForeignKey("candidate_factors.id", ondelete="RESTRICT"), index=True
    )
    observation_id: Mapped[int | None] = mapped_column(
        ForeignKey("observations.id", ondelete="RESTRICT"), index=True
    )
    source_type: Mapped[str] = mapped_column(String(30), nullable=False)
    field_path: Mapped[str | None] = mapped_column(String(500))
    source_reference_json: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )

    decision_step: Mapped[DecisionStep | None] = relationship()
    candidate_factor: Mapped[CandidateFactor | None] = relationship()
    observation: Mapped[Observation | None] = relationship()

    __table_args__ = (
        UniqueConstraint(
            "decision_step_id", "observation_id", name="uq_evidence_step_observation"
        ),
        UniqueConstraint(
            "candidate_factor_id", "observation_id", name="uq_evidence_factor_observation"
        ),
        CheckConstraint(
            "(decision_step_id IS NOT NULL AND candidate_factor_id IS NULL) OR "
            "(decision_step_id IS NULL AND candidate_factor_id IS NOT NULL)",
            name="evidence_exactly_one_owner",
        ),
        CheckConstraint(
            "source_type IN ('observation','rule_source')",
            name="evidence_source_type",
        ),
        CheckConstraint(
            "(source_type = 'observation' AND observation_id IS NOT NULL) OR "
            "(source_type = 'rule_source' AND observation_id IS NULL)",
            name="evidence_source_reference",
        ),
    )


class Correction(TimestampMixin, Base):
    __tablename__ = "corrections"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    certificate_id: Mapped[int] = mapped_column(
        ForeignKey("mill_certificates.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    previous_observation_id: Mapped[int | None] = mapped_column(
        ForeignKey("observations.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    replacement_observation_id: Mapped[int] = mapped_column(
        ForeignKey("observations.id", ondelete="RESTRICT"), nullable=False, unique=True, index=True
    )
    person_name: Mapped[str] = mapped_column(String(200), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    workstation_name: Mapped[str] = mapped_column(String(200), nullable=False)


class ApprovalEvent(TimestampMixin, Base):
    __tablename__ = "approval_events"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    classification_run_id: Mapped[int] = mapped_column(
        ForeignKey("classification_runs.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    from_status: Mapped[str] = mapped_column(String(30), nullable=False)
    to_status: Mapped[str] = mapped_column(String(30), nullable=False)
    person_name: Mapped[str] = mapped_column(String(200), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    workstation_name: Mapped[str] = mapped_column(String(200), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "from_status IN ('draft','needs_review','approved','rejected')",
            name="valid_from_status",
        ),
        CheckConstraint(
            "to_status IN ('draft','needs_review','approved','rejected')",
            name="valid_to_status",
        ),
    )
