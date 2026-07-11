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


def test_queue_info_second_job_has_eta(db_session, job_service):
    from datetime import timedelta

    t0 = datetime.now(timezone.utc)
    TaskJobRepository(db_session).create(
        TaskJob(
            job_type="rfq_analysis",
            ref_id="task-1",
            status="queued",
            queued_at=t0,
            created_at=t0,
            updated_at=t0,
        )
    )
    second = TaskJob(
        job_type="rfq_analysis",
        ref_id="task-2",
        status="queued",
        queued_at=t0 + timedelta(seconds=1),
        created_at=t0,
        updated_at=t0,
    )
    TaskJobRepository(db_session).create(second)
    info = job_service.get_queue_info(db_session, second)
    assert info["queue_position"] == 2
    assert info["estimated_wait_seconds"] == 60


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


def test_timing_payload_queued_running_completed(job_service):
    from datetime import timedelta

    t0 = datetime(2026, 7, 11, 11, 0, 0, tzinfo=timezone.utc)
    queued = TaskJob(
        job_type="rfq_analysis",
        ref_id="t1",
        status="queued",
        queued_at=t0,
        created_at=t0,
        updated_at=t0,
    )
    now = t0 + timedelta(seconds=12)
    q = TaskJobService.timing_payload(queued, now=now)
    assert q["queue_wait_ms"] == 12000
    assert q["run_ms"] is None
    assert q["queued_at"] is not None

    running = TaskJob(
        job_type="rfq_analysis",
        ref_id="t1",
        status="running",
        queued_at=t0,
        started_at=t0 + timedelta(seconds=5),
        created_at=t0,
        updated_at=t0,
    )
    r = TaskJobService.timing_payload(running, now=t0 + timedelta(seconds=25))
    assert r["queue_wait_ms"] == 5000
    assert r["run_ms"] == 20000

    done = TaskJob(
        job_type="rfq_analysis",
        ref_id="t1",
        status="completed",
        queued_at=t0,
        started_at=t0 + timedelta(seconds=5),
        finished_at=t0 + timedelta(seconds=65),
        created_at=t0,
        updated_at=t0,
    )
    c = TaskJobService.timing_payload(done, now=t0 + timedelta(hours=1))
    assert c["queue_wait_ms"] == 5000
    assert c["run_ms"] == 60000
    assert c["finished_at"] is not None


def test_mark_failed_resets_queued_at_on_requeue(db_session, job_service):
    from datetime import timedelta

    job = job_service.enqueue(db_session, job_type="rfq_analysis", ref_id="task-retry")
    original_queued = job.queued_at
    job.attempts = 1
    job.max_attempts = 3
    job.started_at = original_queued
    job_service.mark_failed(db_session, job, "boom")
    reloaded = TaskJobRepository(db_session).get_by_id(job.id)
    assert reloaded.status == "queued"
    assert reloaded.started_at is None
    assert reloaded.finished_at is None
    assert reloaded.queued_at is not None
    assert reloaded.queued_at >= original_queued


def test_mark_completed_stores_timing_snapshot(db_session, job_service):
    from datetime import timedelta

    t0 = datetime.now(timezone.utc) - timedelta(seconds=30)
    job = TaskJob(
        job_type="rfq_analysis",
        ref_id="task-done",
        status="running",
        queued_at=t0,
        started_at=t0 + timedelta(seconds=10),
        created_at=t0,
        updated_at=t0,
        progress_total=3,
    )
    TaskJobRepository(db_session).create(job)
    done = job_service.mark_completed(db_session, job, {"ok": True})
    assert done.status == "completed"
    assert done.result_summary is not None
    assert done.result_summary.get("ok") is True
    timing = done.result_summary.get("timing") or {}
    assert timing.get("queue_wait_ms") == 10000
    assert timing.get("run_ms") is not None
    assert timing["run_ms"] >= 0
