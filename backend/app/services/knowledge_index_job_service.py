from __future__ import annotations

import logging
import time
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

logger = logging.getLogger(__name__)


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
            logger.info(
                "kb_job_deduped job_id=%s mode=%s triggered_by=%s",
                existing.id,
                mode,
                triggered_by,
            )
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
            logger.info(
                "kb_job_enqueued job_id=%s mode=%s triggered_by=%s batch_id=%s",
                created.id,
                mode,
                triggered_by,
                batch_id,
            )
            return created, False
        except IntegrityError:
            db.rollback()
            existing = repo.get_active_by_single_flight(TaskJobService.JOB_KB_INDEX, key)
            if existing is None:
                raise
            logger.info(
                "kb_job_deduped job_id=%s mode=%s triggered_by=%s",
                existing.id,
                mode,
                triggered_by,
            )
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
            logger.info(
                "kb_job_generation job_id=%s generation_id=%s",
                job.id,
                generation_id,
            )

        mode = (job.payload or {}).get("mode", "full")
        started = time.monotonic()
        logger.info("kb_job_execute_start job_id=%s mode=%s", job.id, mode)
        result = EngagementIngestService(self.settings, db).import_all(
            progress_callback=report_progress,
            cancel_check=cancel_requested,
            created_by_job_id=job.id,
            generation_callback=record_generation,
            index_request_type=(
                "kb_incremental" if mode == "incremental" else "kb_full"
            ),
            mode=mode,
        )
        logger.info(
            "kb_job_execute_done job_id=%s mode=%s new_chunks=%s skipped=%s "
            "failed=%s elapsed_ms=%d",
            job.id,
            mode,
            result.get("new_chunks"),
            result.get("skipped"),
            len(result.get("failed_files") or []),
            int((time.monotonic() - started) * 1000),
        )
        return result

    @staticmethod
    def display_progress(job: TaskJob) -> int:
        """Map job phase to a UI percent that stays <100 until the job completes.

        Parsing uses file counts; embedding/validate/switch/finalize are long-running
        stages that historically reported current==total and looked "done" while still running.
        """
        if job.status == "completed":
            return 100
        phase = job.phase or ""
        phase_floor = {
            "queued": 0,
            "scanning": 5,
            "embedding": 85,
            "validating": 92,
            "switching": 95,
            "finalizing": 98,
        }
        if phase in phase_floor and phase != "parsing":
            return phase_floor[phase]
        total = job.progress_total or 0
        current = job.progress_current or 0
        if total <= 0:
            return phase_floor.get(phase, 0)
        # parsing (and any count-based phase): 5% .. 80%
        pct = 5 + round((max(0, current) / total) * 75)
        return min(80, max(5, pct))

    def serialize(self, db: Session, job: TaskJob) -> dict[str, Any]:
        queue = self.jobs.get_queue_info(db, job)
        total = job.progress_total or 0
        progress = self.display_progress(job)
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
