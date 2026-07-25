from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.models.task_job import TaskJob
from app.repositories.task_job_repository import TaskJobRepository
from app.utils.datetime_utils import to_api_utc_iso


class TaskJobService:
    JOB_RFQ_ANALYSIS = "rfq_analysis"
    JOB_RFQ_CONFIRM = "rfq_confirm"
    JOB_KB_INDEX = "kb_index"

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
        priority: int = 0,
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
            priority=priority,
            queued_at=now,
            created_at=now,
            updated_at=now,
        )
        return repo.create(job)

    @staticmethod
    def _aware(dt: datetime | None) -> datetime | None:
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

    @classmethod
    def timing_payload(
        cls,
        job: TaskJob | None,
        *,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        empty: dict[str, Any] = {
            "queue_wait_ms": None,
            "run_ms": None,
            "queued_at": None,
            "started_at": None,
            "finished_at": None,
        }
        if job is None:
            return empty

        now = now or datetime.now(timezone.utc)
        queued = cls._aware(job.queued_at)
        started = cls._aware(job.started_at)
        finished = cls._aware(job.finished_at)

        queue_wait_ms: int | None = None
        if queued is not None:
            if started is not None:
                queue_wait_ms = max(0, int((started - queued).total_seconds() * 1000))
            elif job.status == "queued":
                queue_wait_ms = max(0, int((now - queued).total_seconds() * 1000))
            elif finished is not None:
                queue_wait_ms = max(0, int((finished - queued).total_seconds() * 1000))

        run_ms: int | None = None
        if started is not None:
            end_run = finished if finished is not None else now
            run_ms = max(0, int((end_run - started).total_seconds() * 1000))

        return {
            "queue_wait_ms": queue_wait_ms,
            "run_ms": run_ms,
            "queued_at": to_api_utc_iso(queued),
            "started_at": to_api_utc_iso(started),
            "finished_at": to_api_utc_iso(finished),
        }

    def mark_completed(
        self,
        db: Session,
        job: TaskJob,
        result_summary: dict[str, Any] | None = None,
    ) -> TaskJob:
        repo = TaskJobRepository(db)
        now = datetime.now(timezone.utc)
        job.status = "completed"
        job.phase = "completed"
        job.progress_current = job.progress_total
        job.heartbeat_at = now
        job.finished_at = now
        job.error_message = None
        job.updated_at = now
        summary = dict(result_summary or {})
        timing = self.timing_payload(job, now=now)
        summary["timing"] = {
            "queue_wait_ms": timing["queue_wait_ms"],
            "run_ms": timing["run_ms"],
        }
        job.result_summary = summary
        return repo.update(job)

    def update_progress(
        self,
        db: Session,
        job: TaskJob,
        *,
        phase: str,
        current: int,
        total: int,
    ) -> TaskJob:
        job.phase = phase
        job.progress_current = max(0, current)
        job.progress_total = max(0, total)
        job.heartbeat_at = datetime.now(timezone.utc)
        return TaskJobRepository(db).update(job)

    def request_cancel(self, db: Session, job: TaskJob) -> TaskJob:
        if job.status in {"completed", "failed", "cancelled"}:
            return job
        now = datetime.now(timezone.utc)
        job.cancel_requested_at = now
        if job.status == "queued":
            job.status = "cancelled"
            job.phase = "cancelled"
            job.finished_at = now
        return TaskJobRepository(db).update(job)

    def mark_cancelled(self, db: Session, job: TaskJob) -> TaskJob:
        now = datetime.now(timezone.utc)
        job.status = "cancelled"
        job.phase = "cancelled"
        job.finished_at = now
        job.heartbeat_at = now
        return TaskJobRepository(db).update(job)

    def mark_failed(self, db: Session, job: TaskJob, error: str) -> TaskJob:
        repo = TaskJobRepository(db)
        now = datetime.now(timezone.utc)
        job.error_message = error[:2000]
        job.updated_at = now
        if job.attempts >= job.max_attempts:
            job.status = "failed"
            job.finished_at = now
        else:
            job.status = "queued"
            job.worker_id = None
            job.started_at = None
            job.heartbeat_at = None
            job.finished_at = None
            job.queued_at = now
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
