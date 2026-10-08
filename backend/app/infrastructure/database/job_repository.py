"""PostgreSQL-backed queue with safe concurrent claims."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from backend.app.domain.enums import ProcessingStatus
from backend.app.infrastructure.database.models import Job


class JobRepository:
    def claim_next(self, session: Session, worker_id: str) -> Job | None:
        job = session.scalar(
            select(Job)
            .where(
                Job.status == ProcessingStatus.QUEUED.value,
                Job.attempts < Job.max_attempts,
            )
            .order_by(Job.created_at, Job.id)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if job is None:
            return None
        now = datetime.now(timezone.utc)
        job.status = ProcessingStatus.RUNNING.value
        job.worker_id = worker_id
        job.started_at = job.started_at or now
        job.heartbeat_at = now
        job.attempts += 1
        job.progress = max(job.progress, 1)
        session.flush()
        return job

    def recover_stale(self, session: Session, stale_after_seconds: int) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=stale_after_seconds)
        jobs = session.scalars(
            select(Job)
            .where(
                Job.status == ProcessingStatus.RUNNING.value,
                or_(Job.heartbeat_at.is_(None), Job.heartbeat_at < cutoff),
            )
            .with_for_update(skip_locked=True)
        ).all()
        for job in jobs:
            job.worker_id = None
            job.heartbeat_at = None
            if job.attempts >= job.max_attempts:
                job.status = ProcessingStatus.FAILED.value
                job.error_code = "worker_interrupted"
                job.error_message = "El trabajo excedió el máximo de intentos tras una interrupción"
                job.finished_at = datetime.now(timezone.utc)
            else:
                job.status = ProcessingStatus.QUEUED.value
        return len(jobs)

