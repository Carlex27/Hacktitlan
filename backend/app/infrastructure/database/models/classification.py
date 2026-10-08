from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import BigInteger, CheckConstraint, Date, ForeignKey, Identity, Index, Integer, JSON, String, Text, UniqueConstraint
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

