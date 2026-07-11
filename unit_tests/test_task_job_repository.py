from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.task_job import TaskJob
from app.repositories.task_job_repository import TaskJobRepository


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


def _job(ref_id: str, *, status: str = "queued", queued_at: datetime | None = None) -> TaskJob:
    now = queued_at or datetime.now(timezone.utc)
    return TaskJob(
        job_type="rfq_analysis",
        ref_id=ref_id,
        status=status,
        queued_at=now,
        created_at=now,
        updated_at=now,
    )


def test_create_and_get_by_id(db_session):
    repo = TaskJobRepository(db_session)
    job = repo.create(_job("task-1"))
    loaded = repo.get_by_id(job.id)
    assert loaded is not None
    assert loaded.ref_id == "task-1"
    assert loaded.status == "queued"


def test_claim_next_marks_running(db_session):
    repo = TaskJobRepository(db_session)
    job = repo.create(_job("task-1"))
    claimed = repo.claim_next("worker-a")
    assert claimed is not None
    assert claimed.id == job.id
    assert claimed.status == "running"
    assert claimed.worker_id == "worker-a"
    assert claimed.attempts == 1


def test_claim_next_fifo(db_session):
    repo = TaskJobRepository(db_session)
    t0 = datetime.now(timezone.utc)
    repo.create(_job("older", queued_at=t0))
    repo.create(_job("newer", queued_at=t0 + timedelta(seconds=1)))
    claimed = repo.claim_next("worker-a")
    assert claimed is not None
    assert claimed.ref_id == "older"


def test_count_queued_before(db_session):
    repo = TaskJobRepository(db_session)
    t0 = datetime.now(timezone.utc)
    repo.create(_job("a", queued_at=t0))
    middle = repo.create(_job("b", queued_at=t0 + timedelta(seconds=1)))
    repo.create(_job("c", queued_at=t0 + timedelta(seconds=2)))
    assert repo.count_queued_before(middle) == 1


def test_reset_stale_running(db_session):
    repo = TaskJobRepository(db_session)
    stale = _job("stale", status="running")
    stale.started_at = datetime.now(timezone.utc) - timedelta(hours=3)
    repo.create(stale)
    reset = repo.reset_stale_running(older_than=datetime.now(timezone.utc) - timedelta(hours=2))
    assert reset == 1
    reloaded = repo.get_by_id(stale.id)
    assert reloaded.status == "queued"


def test_get_latest_by_ref_includes_completed(db_session):
    repo = TaskJobRepository(db_session)
    t0 = datetime.now(timezone.utc)
    older = _job("task-1", status="completed", queued_at=t0)
    older.finished_at = t0
    repo.create(older)
    newer = _job("task-1", status="failed", queued_at=t0 + timedelta(seconds=5))
    newer.created_at = t0 + timedelta(seconds=5)
    repo.create(newer)
    latest = repo.get_latest_by_ref("rfq_analysis", "task-1")
    assert latest is not None
    assert latest.id == newer.id
    assert latest.status == "failed"
