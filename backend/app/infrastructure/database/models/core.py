from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Identity,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.domain.enums import ApprovalStatus, FileStatus, ProcessingStatus
from backend.app.infrastructure.database.models.common import TimestampMixin
from backend.app.infrastructure.database.session import Base


class Manufacturer(TimestampMixin, Base):
    __tablename__ = "manufacturers"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(300), nullable=False, unique=True)


class StoredFile(TimestampMixin, Base):
    __tablename__ = "stored_files"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    original_name: Mapped[str] = mapped_column(String(500), nullable=False)
    storage_name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    relative_path: Mapped[str] = mapped_column(String(1000), nullable=False, unique=True)
    media_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default=FileStatus.READY.value)

    __table_args__ = (
        CheckConstraint("char_length(sha256) = 64", name="sha256_length"),
        CheckConstraint("size_bytes >= 0", name="size_nonnegative"),
        CheckConstraint(
            "status IN ('ready','quarantined','missing')", name="valid_status"
        ),
    )


class Document(TimestampMixin, Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    stored_file_id: Mapped[int] = mapped_column(
        ForeignKey("stored_files.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    processing_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default=ProcessingStatus.QUEUED.value, index=True
    )
    page_count: Mapped[int | None] = mapped_column(Integer)
    language: Mapped[str | None] = mapped_column(String(30))
    archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    stored_file: Mapped[StoredFile] = relationship()

    __table_args__ = (
        CheckConstraint(
            "processing_status IN ('queued','running','succeeded','needs_review',"
            "'needs_ocr','failed','cancelled')",
            name="valid_processing_status",
        ),
    )


class MillCertificate(TimestampMixin, Base):
    __tablename__ = "mill_certificates"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="RESTRICT"), nullable=False, unique=True, index=True
    )
    manufacturer_id: Mapped[int | None] = mapped_column(
        ForeignKey("manufacturers.id", ondelete="RESTRICT"), index=True
    )
    certificate_no: Mapped[str | None] = mapped_column(String(200), index=True)
    certificate_date: Mapped[date | None] = mapped_column(Date, index=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    previous_revision_id: Mapped[int | None] = mapped_column(
        ForeignKey("mill_certificates.id", ondelete="RESTRICT"), index=True
    )
    approval_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default=ApprovalStatus.DRAFT.value, index=True
    )
    standard: Mapped[str | None] = mapped_column(String(500))
    product_name: Mapped[str | None] = mapped_column(String(500))
    demo_notice: Mapped[str] = mapped_column(String(200), nullable=False)

    document: Mapped[Document] = relationship()
    manufacturer: Mapped[Manufacturer | None] = relationship()
    previous_revision: Mapped[MillCertificate | None] = relationship(remote_side="MillCertificate.id")

    __table_args__ = (
        UniqueConstraint(
            "manufacturer_id", "certificate_no", "revision_number",
            name="uq_certificate_manufacturer_number_revision",
        ),
        CheckConstraint("revision_number >= 1", name="revision_positive"),
        CheckConstraint(
            "approval_status IN ('draft','needs_review','approved','rejected')",
            name="valid_approval_status",
        ),
        Index("ix_certificates_date_id", "certificate_date", "id"),
        Index("ix_certificates_uploaded_id", "uploaded_at", "id"),
    )


class Heat(TimestampMixin, Base):
    __tablename__ = "heats"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    certificate_id: Mapped[int] = mapped_column(
        ForeignKey("mill_certificates.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    heat_no: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    standard: Mapped[str | None] = mapped_column(String(500))
    grade: Mapped[str | None] = mapped_column(String(200))
    properties_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    certificate: Mapped[MillCertificate] = relationship()

    __table_args__ = (
        UniqueConstraint("certificate_id", "heat_no", name="uq_heat_certificate_number"),
        Index("ix_heats_number_id", "heat_no", "id"),
    )


class Product(TimestampMixin, Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    certificate_id: Mapped[int] = mapped_column(
        ForeignKey("mill_certificates.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    heat_id: Mapped[int | None] = mapped_column(
        ForeignKey("heats.id", ondelete="RESTRICT"), index=True
    )
    product_identifier: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    label_no: Mapped[str | None] = mapped_column(String(300))
    product_type: Mapped[str | None] = mapped_column(String(200))
    form: Mapped[str | None] = mapped_column(String(100))
    coiled: Mapped[bool | None] = mapped_column(Boolean)
    rolling: Mapped[str | None] = mapped_column(String(50))
    width_mm: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    thickness_mm: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    length_m: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    net_weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    gross_weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    properties_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    certificate: Mapped[MillCertificate] = relationship()
    heat: Mapped[Heat | None] = relationship()

    __table_args__ = (
        UniqueConstraint(
            "certificate_id", "product_identifier", name="uq_product_certificate_identifier"
        ),
        Index("ix_products_heat_id_id", "heat_id", "id"),
    )


class Observation(TimestampMixin, Base):
    __tablename__ = "observations"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    certificate_id: Mapped[int] = mapped_column(
        ForeignKey("mill_certificates.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    heat_id: Mapped[int | None] = mapped_column(ForeignKey("heats.id"), index=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), index=True)
    field_path: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    raw_value_json: Mapped[Any | None] = mapped_column(JSON)
    normalized_value_json: Mapped[Any | None] = mapped_column(JSON)
    verification_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    unit: Mapped[str | None] = mapped_column(String(50))
    confidence: Mapped[float | None] = mapped_column(Float)
    page_number: Mapped[int | None] = mapped_column(Integer)
    bbox_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    source_text: Mapped[str | None] = mapped_column(Text)
    inherited: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    supersedes_id: Mapped[int | None] = mapped_column(
        ForeignKey("observations.id", ondelete="RESTRICT"), index=True
    )
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)

    supersedes: Mapped[Observation | None] = relationship(remote_side="Observation.id")

    __table_args__ = (
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="confidence_range",
        ),
        CheckConstraint("page_number IS NULL OR page_number >= 1", name="page_positive"),
        Index("ix_observations_certificate_field", "certificate_id", "field_path"),
    )


class ChemicalComposition(TimestampMixin, Base):
    __tablename__ = "chemical_compositions"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    heat_id: Mapped[int | None] = mapped_column(ForeignKey("heats.id"), index=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), index=True)
    element: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    raw_value_json: Mapped[Any | None] = mapped_column(JSON)
    percentage: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    inherited: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    source_label: Mapped[str | None] = mapped_column(String(100))

    __table_args__ = (
        CheckConstraint(
            "(heat_id IS NOT NULL AND product_id IS NULL) OR "
            "(heat_id IS NULL AND product_id IS NOT NULL)",
            name="exactly_one_scope",
        ),
        CheckConstraint(
            "percentage IS NULL OR (percentage >= 0 AND percentage <= 100)",
            name="percentage_range",
        ),
        Index("ix_chemistry_heat_element", "heat_id", "element"),
        Index("ix_chemistry_product_element", "product_id", "element"),
    )
