from datetime import datetime, timezone

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.models.task_job import TaskJob


class TaskJobRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, job: TaskJob) -> TaskJob:
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def get_by_id(self, job_id: str) -> TaskJob | None:
        return self.db.get(TaskJob, job_id)

    def get_active_by_ref(self, job_type: str, ref_id: str) -> TaskJob | None:
        stmt = (
            select(TaskJob)
            .where(
                TaskJob.job_type == job_type,
                TaskJob.ref_id == ref_id,
                TaskJob.status.in_(("queued", "running")),
            )
            .order_by(TaskJob.created_at.desc())
            .limit(1)
        )
        return self.db.scalar(stmt)

    def update(self, job: TaskJob) -> TaskJob:
        job.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(job)
        return job

    def claim_next(self, worker_id: str) -> TaskJob | None:
        dialect = self.db.bind.dialect.name if self.db.bind else "sqlite"
        if dialect == "postgresql":
            row = self.db.execute(
                text(
                    """
                    SELECT id FROM task_jobs
                    WHERE status = 'queued'
                    ORDER BY queued_at ASC
                    FOR UPDATE SKIP LOCKED
                    LIMIT 1
                    """
                )
            ).first()
            if not row:
                return None
            job = self.get_by_id(row[0])
        else:
            job = self.db.scalar(
                select(TaskJob)
                .where(TaskJob.status == "queued")
                .order_by(TaskJob.queued_at.asc())
                .limit(1)
            )
            if not job:
                return None

        now = datetime.now(timezone.utc)
        job.status = "running"
        job.worker_id = worker_id
        job.started_at = now
        job.attempts = (job.attempts or 0) + 1
        job.updated_at = now
        self.db.commit()
        self.db.refresh(job)
        return job

    def count_queued_before(self, job: TaskJob) -> int:
        if job.status != "queued":
            return 0
        stmt = (
            select(func.count())
            .select_from(TaskJob)
            .where(
                TaskJob.status == "queued",
                TaskJob.queued_at < job.queued_at,
            )
        )
        return int(self.db.scalar(stmt) or 0)

    def count_queued(self) -> int:
        stmt = select(func.count()).select_from(TaskJob).where(TaskJob.status == "queued")
        return int(self.db.scalar(stmt) or 0)

    def count_running(self) -> int:
        stmt = select(func.count()).select_from(TaskJob).where(TaskJob.status == "running")
        return int(self.db.scalar(stmt) or 0)

    def reset_stale_running(self, *, older_than: datetime) -> int:
        jobs = list(
            self.db.scalars(
                select(TaskJob).where(
                    TaskJob.status == "running",
                    TaskJob.started_at.isnot(None),
                    TaskJob.started_at < older_than,
                )
            )
        )
        for job in jobs:
            job.status = "queued"
            job.worker_id = None
            job.started_at = None
            job.updated_at = datetime.now(timezone.utc)
        if jobs:
            self.db.commit()
        return len(jobs)
