"""Draft format library and isolated document preparation/preview artifacts."""
from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Identity, Index, Integer, JSON, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column
from pydantic import JsonValue

from backend.app.infrastructure.database.models.common import TimestampMixin
from backend.app.infrastructure.database.session import Base


class CertificateFormat(TimestampMixin, Base):
    __tablename__ = "certificate_formats"
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), nullable=False, default="")


class CertificateFormatVersion(TimestampMixin, Base):
    __tablename__ = "certificate_format_versions"
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    format_id: Mapped[int] = mapped_column(ForeignKey("certificate_formats.id", ondelete="RESTRICT"), index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    configuration_json: Mapped[dict[str, JsonValue]] = mapped_column(JSON, nullable=False)
    configuration_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    person_name: Mapped[str] = mapped_column(String(200), nullable=False)
    reason: Mapped[str] = mapped_column(String(4000), nullable=False)
    lifecycle_json: Mapped[list[dict[str, JsonValue]]] = mapped_column(JSON, nullable=False, default=list, server_default="[]")
    __table_args__ = (
        UniqueConstraint("format_id", "version_number"),
        CheckConstraint("version_number > 0 AND revision > 0", name="positive_revision"),
        CheckConstraint("status IN ('draft','active','retired')", name="valid_format_status"),
        Index("uq_format_active_version", "format_id", unique=True, postgresql_where=text("status = 'active'")),
    )


class PreparedDocumentLayout(TimestampMixin, Base):
    __tablename__ = "prepared_document_layouts"
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    job_id: Mapped[int | None] = mapped_column(ForeignKey("jobs.id", ondelete="SET NULL"), unique=True)
    document_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    layout_json: Mapped[dict[str, JsonValue]] = mapped_column(JSON, nullable=False)


class CertificateFormatTest(TimestampMixin, Base):
    __tablename__ = "certificate_format_tests"
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    version_id: Mapped[int] = mapped_column(ForeignKey("certificate_format_versions.id", ondelete="RESTRICT"), index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    layout_id: Mapped[int] = mapped_column(ForeignKey("prepared_document_layouts.id", ondelete="CASCADE"), index=True)
    job_id: Mapped[int | None] = mapped_column(ForeignKey("jobs.id", ondelete="SET NULL"), unique=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    configuration_json: Mapped[dict[str, JsonValue]] = mapped_column(JSON, nullable=False)
    configuration_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    extractor_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    result_json: Mapped[dict[str, JsonValue] | None] = mapped_column(JSON)
    reviewed_by: Mapped[str | None] = mapped_column(String(200))
    review_reason: Mapped[str | None] = mapped_column(String(4000))
