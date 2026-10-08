from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Identity, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.infrastructure.database.models.common import TimestampMixin
from backend.app.infrastructure.database.session import Base


class Export(TimestampMixin, Base):
    __tablename__ = "exports"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    classification_run_id: Mapped[int | None] = mapped_column(
        ForeignKey("classification_runs.id", ondelete="RESTRICT"), index=True
    )
    stored_file_id: Mapped[int | None] = mapped_column(
        ForeignKey("stored_files.id", ondelete="RESTRICT"), index=True
    )
    format: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    scope_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    filters_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    person_name: Mapped[str] = mapped_column(String(200), nullable=False)
    workstation_name: Mapped[str] = mapped_column(String(200), nullable=False)
    sha256: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        CheckConstraint("format IN ('xlsx','csv','pdf')", name="valid_format"),
        CheckConstraint(
            "status IN ('queued','running','succeeded','failed')", name="valid_status"
        ),
    )


class BackupRun(TimestampMixin, Base):
    __tablename__ = "backup_runs"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(30), nullable=False)
    primary_path: Mapped[str | None] = mapped_column(String(1000))
    secondary_path: Mapped[str | None] = mapped_column(String(1000))
    manifest_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    sha256: Mapped[str | None] = mapped_column(String(64))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        CheckConstraint(
            "status IN ('queued','running','succeeded','failed','verified')",
            name="valid_status",
        ),
        CheckConstraint("kind IN ('daily','weekly','monthly','manual')", name="valid_kind"),
    )

