from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.models.task_job import TaskJob
from app.repositories.task_job_repository import TaskJobRepository
from app.services.disk_guard_service import DiskGuardService
from app.services.engagement_ingest_service import EngagementIngestService
from app.services.knowledge_import_service import KnowledgeImportService
from app.services.task_job_service import TaskJobService


class KnowledgeIndexJobService:
    SINGLE_FLIGHT_KEY = "kb_index:production"

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.jobs = TaskJobService(self.settings)

    def enqueue(
        self,
        db: Session,
        *,
        mode: str,
        triggered_by: str | None,
        batch_id: str | None = None,
    ) -> tuple[TaskJob, bool]:
        repo = TaskJobRepository(db)
        key = f"kb_index:{self.settings.knowledge_vector_namespace}"
        existing = repo.get_active_by_single_flight(TaskJobService.JOB_KB_INDEX, key)
        if existing:
            return existing, True

        now = datetime.now(timezone.utc)
        job = TaskJob(
            job_type=TaskJobService.JOB_KB_INDEX,
            ref_id=self.settings.knowledge_vector_namespace,
            status="queued",
            phase="queued",
            priority=200 if mode == "incremental" else 100,
            single_flight_key=key,
            payload={
                "mode": mode,
                "batch_id": batch_id,
                "logical_namespace": self.settings.knowledge_vector_namespace,
                "triggered_by": triggered_by,
            },
            queued_at=now,
            created_at=now,
            updated_at=now,
        )
        try:
            created = repo.create(job)
            KnowledgeImportService(db).create_for_job(created)
            return created, False
        except IntegrityError:
            db.rollback()
            existing = repo.get_active_by_single_flight(TaskJobService.JOB_KB_INDEX, key)
            if existing is None:
                raise
            return existing, True

    def sync_import_started(self, db: Session, job: TaskJob) -> None:
        KnowledgeImportService(db).sync_job_started(job)

    def sync_import_finished(
        self,
        db: Session,
        job: TaskJob,
        *,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        KnowledgeImportService(db).sync_job_finished(
            job, result=result, error=error
        )

    def get(self, db: Session, job_id: str) -> TaskJob | None:
        job = TaskJobRepository(db).get_by_id(job_id)
        if job is None or job.job_type != TaskJobService.JOB_KB_INDEX:
            return None
        return job

    def get_active(self, db: Session) -> TaskJob | None:
        return TaskJobRepository(db).get_active_by_type(TaskJobService.JOB_KB_INDEX)

    def list(self, db: Session, *, limit: int, offset: int) -> list[TaskJob]:
        return TaskJobRepository(db).list_by_type(
            TaskJobService.JOB_KB_INDEX,
            limit=limit,
            offset=offset,
        )

    def cancel(self, db: Session, job: TaskJob) -> TaskJob:
        return self.jobs.request_cancel(db, job)

    def execute(self, db: Session, job: TaskJob) -> dict[str, Any]:
        DiskGuardService(self.settings).assert_writable(include_temp=True)

        def report_progress(phase: str, current: int, total: int) -> None:
            self.jobs.update_progress(
                db,
                job,
                phase=phase,
                current=current,
                total=total,
            )

        def cancel_requested() -> bool:
            db.expire(job)
            db.refresh(job)
            return job.cancel_requested_at is not None

        def record_generation(generation_id: str) -> None:
            job.payload = {**(job.payload or {}), "generation_id": generation_id}
            TaskJobRepository(db).update(job)

        mode = (job.payload or {}).get("mode", "full")
        return EngagementIngestService(self.settings, db).import_all(
            progress_callback=report_progress,
            cancel_check=cancel_requested,
            created_by_job_id=job.id,
            generation_callback=record_generation,
            index_request_type=(
                "kb_incremental" if mode == "incremental" else "kb_full"
            ),
        )

    def serialize(self, db: Session, job: TaskJob) -> dict[str, Any]:
        queue = self.jobs.get_queue_info(db, job)
        total = job.progress_total or 0
        progress = round((job.progress_current / total) * 100) if total else 0
        data: dict[str, Any] = {
            "job_id": job.id,
            "status": "cancelling"
            if job.status == "running" and job.cancel_requested_at
            else job.status,
            "phase": job.phase,
            "progress": progress,
            "progress_current": job.progress_current,
            "progress_total": total,
            "queue_position": queue["queue_position"],
            "estimated_wait_seconds": queue["estimated_wait_seconds"],
            "triggered_by": (job.payload or {}).get("triggered_by"),
            "mode": (job.payload or {}).get("mode"),
            "batch_id": (job.payload or {}).get("batch_id"),
            "generation_id": (job.payload or {}).get("generation_id"),
            "error": job.error_message,
            "created_at": job.created_at,
            "started_at": job.started_at,
            "finished_at": job.finished_at,
        }
        if job.result_summary:
            data.update(job.result_summary)
        import_record = KnowledgeImportService(db).get_by_job(job.id)
        if import_record is not None:
            data["import_id"] = import_record.id
        return data
