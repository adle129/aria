from __future__ import annotations

import logging
import socket
import time
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import SessionLocal
from app.models.task_job import TaskJob
from app.repositories.rfq_task_repository import RFQTaskRepository
from app.repositories.task_job_repository import TaskJobRepository
from app.services.engagement_ingest_service import EngagementIngestCancelled
from app.services.knowledge_index_job_service import KnowledgeIndexJobService
from app.services.ollama_concurrency import get_ollama_gate
from app.services.rfq_analysis_service import RFQAnalysisService
from app.services.task_job_service import TaskJobService

logger = logging.getLogger(__name__)

IN_FLIGHT_RFQ_STATUSES = frozenset({"queued", "pending", "parsing", "retrieving", "generating"})


class WorkerService:
    def __init__(self, settings: Settings | None = None, worker_id: str | None = None):
        self.settings = settings or get_settings()
        self.worker_id = worker_id or f"{socket.gethostname()}-{uuid.uuid4().hex[:8]}"
        self.job_service = TaskJobService(self.settings)
        self.analysis_service = RFQAnalysisService(self.settings)

    def recover_stale_jobs(self, db: Session) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=self.settings.task_job_stale_seconds)
        task_repo = RFQTaskRepository(db)
        jobs = list(
            db.scalars(
                select(TaskJob).where(
                    TaskJob.status == "running",
                    TaskJob.started_at.isnot(None),
                    func.coalesce(TaskJob.heartbeat_at, TaskJob.started_at) < cutoff,
                )
            )
        )
        if not jobs:
            return 0

        for job in jobs:
            self.job_service.mark_failed(db, job, "任务执行超时（worker 无响应）")
            if job.job_type == TaskJobService.JOB_RFQ_ANALYSIS:
                task = task_repo.get_by_id(job.ref_id)
                if task and task.processing_status in IN_FLIGHT_RFQ_STATUSES:
                    if job.status == "queued":
                        task.processing_status = "queued"
                        task.error_msg = None
                        task.progress = "0"
                        task.status_message = "任务超时，正在重新排队..."
                    else:
                        task.processing_status = "failed"
                        task.error_msg = "分析超时：本地模型响应过慢或处理中断"
                        task.status_message = "分析失败"
                    task_repo.update(task)
        return len(jobs)

    def process_job(self, db: Session, job: TaskJob) -> dict | None:
        if job.job_type == TaskJobService.JOB_RFQ_ANALYSIS:
            gate = get_ollama_gate(self.settings)
            with gate.acquire():
                self.analysis_service.analyze_task(db, job.ref_id)
            return None
        if job.job_type == TaskJobService.JOB_KB_INDEX:
            return KnowledgeIndexJobService(self.settings).execute(db, job)
        raise ValueError(f"Unsupported job_type: {job.job_type}")

    def handle_job(self, db: Session, job: TaskJob) -> None:
        try:
            result = self.process_job(db, job)
            self.job_service.mark_completed(db, job, result)
        except EngagementIngestCancelled:
            self.job_service.mark_cancelled(db, job)
        except Exception as exc:
            logger.exception("Job %s failed", job.id)
            self.job_service.mark_failed(db, job, str(exc))

    def process_one(self, db: Session) -> TaskJob | None:
        repo = TaskJobRepository(db)
        job = repo.claim_next(self.worker_id)
        if not job:
            return None
        self.handle_job(db, job)
        return job

    def run_once(self) -> bool:
        db = SessionLocal()
        try:
            return self.process_one(db) is not None
        finally:
            db.close()

    def run_forever(self) -> None:
        db = SessionLocal()
        try:
            recovered = self.recover_stale_jobs(db)
            if recovered:
                logger.info("Recovered %s stale running jobs", recovered)
        finally:
            db.close()

        poll = max(0.5, float(self.settings.task_worker_poll_seconds))
        logger.info("Worker %s started (poll=%ss)", self.worker_id, poll)
        while True:
            db = SessionLocal()
            try:
                recovered = self.recover_stale_jobs(db)
                if recovered:
                    logger.info("Recovered %s stale running jobs", recovered)
            finally:
                db.close()
            processed = self.run_once()
            if not processed:
                time.sleep(poll)


def run_inline_job(db: Session, job: TaskJob, settings: Settings | None = None) -> None:
    repo = TaskJobRepository(db)
    now = datetime.now(timezone.utc)
    job.status = "running"
    job.started_at = now
    job.heartbeat_at = now
    job.worker_id = "inline"
    job.attempts = (job.attempts or 0) + 1
    repo.update(job)
    WorkerService(settings).handle_job(db, job)
