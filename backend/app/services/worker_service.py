from __future__ import annotations

import logging
import socket
import time
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import SessionLocal
from app.models.task_job import TaskJob
from app.repositories.task_job_repository import TaskJobRepository
from app.services.ollama_concurrency import get_ollama_gate
from app.services.rfq_analysis_service import RFQAnalysisService
from app.services.task_job_service import TaskJobService

logger = logging.getLogger(__name__)


class WorkerService:
    def __init__(self, settings: Settings | None = None, worker_id: str | None = None):
        self.settings = settings or get_settings()
        self.worker_id = worker_id or f"{socket.gethostname()}-{uuid.uuid4().hex[:8]}"
        self.job_service = TaskJobService(self.settings)
        self.analysis_service = RFQAnalysisService(self.settings)

    def recover_stale_jobs(self, db: Session) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=2)
        return TaskJobRepository(db).reset_stale_running(older_than=cutoff)

    def process_job(self, db: Session, job: TaskJob) -> None:
        if job.job_type == TaskJobService.JOB_RFQ_ANALYSIS:
            gate = get_ollama_gate(self.settings)
            with gate.acquire():
                self.analysis_service.analyze_task(db, job.ref_id)
            return
        raise ValueError(f"Unsupported job_type: {job.job_type}")

    def handle_job(self, db: Session, job: TaskJob) -> None:
        try:
            self.process_job(db, job)
            self.job_service.mark_completed(db, job)
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
            processed = self.run_once()
            if not processed:
                time.sleep(poll)


def run_inline_job(db: Session, job: TaskJob, settings: Settings | None = None) -> None:
    repo = TaskJobRepository(db)
    now = datetime.now(timezone.utc)
    job.status = "running"
    job.started_at = now
    job.worker_id = "inline"
    job.attempts = (job.attempts or 0) + 1
    repo.update(job)
    WorkerService(settings).handle_job(db, job)
