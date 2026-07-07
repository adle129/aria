from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.models.task_job import TaskJob
from app.repositories.task_job_repository import TaskJobRepository


class TaskJobService:
    JOB_RFQ_ANALYSIS = "rfq_analysis"

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    def uses_inline_worker(self) -> bool:
        if self.settings.task_worker_inline:
            return True
        return self.settings.database_url.startswith("sqlite")

    def enqueue(
        self,
        db: Session,
        *,
        job_type: str,
        ref_id: str,
        payload: dict[str, Any] | None = None,
    ) -> TaskJob:
        repo = TaskJobRepository(db)
        existing = repo.get_active_by_ref(job_type, ref_id)
        if existing:
            return existing

        now = datetime.now(timezone.utc)
        job = TaskJob(
            job_type=job_type,
            ref_id=ref_id,
            status="queued",
            payload=payload,
            queued_at=now,
            created_at=now,
            updated_at=now,
        )
        return repo.create(job)

    def mark_completed(self, db: Session, job: TaskJob) -> TaskJob:
        repo = TaskJobRepository(db)
        now = datetime.now(timezone.utc)
        job.status = "completed"
        job.finished_at = now
        job.error_message = None
        job.updated_at = now
        return repo.update(job)

    def mark_failed(self, db: Session, job: TaskJob, error: str) -> TaskJob:
        repo = TaskJobRepository(db)
        now = datetime.now(timezone.utc)
        job.error_message = error[:2000]
        job.finished_at = now
        job.updated_at = now
        if job.attempts >= job.max_attempts:
            job.status = "failed"
        else:
            job.status = "queued"
            job.worker_id = None
            job.started_at = None
        return repo.update(job)

    def get_queue_info(self, db: Session, job: TaskJob | None) -> dict[str, int | None]:
        if job is None or job.status != "queued":
            return {"queue_position": None, "estimated_wait_seconds": None}

        repo = TaskJobRepository(db)
        ahead = repo.count_queued_before(job)
        position = ahead + 1
        running = repo.count_running()
        slots = max(1, int(self.settings.ollama_max_concurrent))
        active_ahead = max(0, running - slots + 1)
        wait_jobs = ahead + active_ahead
        eta = wait_jobs * int(self.settings.task_job_avg_seconds)
        return {"queue_position": position, "estimated_wait_seconds": eta}
