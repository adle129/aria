from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.database import Base
from app.models.task_job import TaskJob
from app.repositories.task_job_repository import TaskJobRepository
from app.services.task_job_service import TaskJobService


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine, tables=[TaskJob.__table__])
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture
def job_service():
    return TaskJobService(
        Settings(
            database_url="sqlite://",
            ollama_max_concurrent=1,
            task_job_avg_seconds=60,
        )
    )


def test_uses_inline_worker_for_sqlite(job_service):
    assert job_service.uses_inline_worker() is True


def test_enqueue_deduplicates_active_job(db_session, job_service):
    first = job_service.enqueue(db_session, job_type="rfq_analysis", ref_id="task-1")
    second = job_service.enqueue(db_session, job_type="rfq_analysis", ref_id="task-1")
    assert first.id == second.id


def test_queue_info_for_queued_job(db_session, job_service):
    now = datetime.now(timezone.utc)
    job = TaskJob(
        job_type="rfq_analysis",
        ref_id="task-1",
        status="queued",
        queued_at=now,
        created_at=now,
        updated_at=now,
    )
    TaskJobRepository(db_session).create(job)
    info = job_service.get_queue_info(db_session, job)
    assert info["queue_position"] == 1
    assert info["estimated_wait_seconds"] == 0


def test_mark_failed_requeues_until_max_attempts(db_session, job_service):
    job = job_service.enqueue(db_session, job_type="rfq_analysis", ref_id="task-1")
    job.attempts = 1
    job.max_attempts = 2
    job_service.mark_failed(db_session, job, "boom")
    reloaded = TaskJobRepository(db_session).get_by_id(job.id)
    assert reloaded.status == "queued"

    reloaded.attempts = 2
    job_service.mark_failed(db_session, reloaded, "boom again")
    final = TaskJobRepository(db_session).get_by_id(job.id)
    assert final.status == "failed"
