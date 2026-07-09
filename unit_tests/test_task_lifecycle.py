"""Unit tests for task lifecycle: retry, delete, archive, stale recovery with retry logic."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.database import Base
from app.models.rfq_task import RFQTask
from app.models.task_job import TaskJob
from app.repositories.rfq_task_repository import RFQTaskRepository
from app.repositories.task_job_repository import TaskJobRepository
from app.services.rfq_analysis_service import RFQAnalysisService
from app.services.task_job_service import TaskJobService
from app.services.worker_service import WorkerService


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture
def settings():
    return Settings(
        database_url="sqlite://",
        mock_llm=True,
        mock_rag=True,
        task_job_stale_seconds=900,
        task_max_queue_size=5,
    )


# ─── Repository ────────────────────────────────────────────────────────────────


def test_rfq_task_delete(db_session):
    task = RFQTask(file_name="a.docx", file_path="/tmp/a.docx", processing_status="failed")
    repo = RFQTaskRepository(db_session)
    repo.create(task)
    assert repo.get_by_id(task.id) is not None

    repo.delete(task)
    assert repo.get_by_id(task.id) is None


def test_list_recent_excludes_archived_by_default(db_session):
    repo = RFQTaskRepository(db_session)
    t1 = RFQTask(file_name="active.docx", file_path="/tmp/a.docx", processing_status="completed")
    t2 = RFQTask(file_name="old.docx", file_path="/tmp/b.docx", processing_status="completed", archived=True)
    repo.create(t1)
    repo.create(t2)

    results = repo.list_recent(unique_file_name=False)
    assert any(t.file_name == "active.docx" for t in results)
    assert not any(t.file_name == "old.docx" for t in results)


def test_list_recent_includes_archived_when_requested(db_session):
    repo = RFQTaskRepository(db_session)
    t1 = RFQTask(file_name="active.docx", file_path="/tmp/a.docx", processing_status="completed")
    t2 = RFQTask(file_name="old.docx", file_path="/tmp/b.docx", processing_status="completed", archived=True)
    repo.create(t1)
    repo.create(t2)

    results = repo.list_recent(unique_file_name=False, include_archived=True)
    names = {t.file_name for t in results}
    assert "active.docx" in names
    assert "old.docx" in names


# ─── RFQAnalysisService.retry_task ─────────────────────────────────────────────


def test_retry_task_resets_state(db_session, settings, tmp_path):
    rfq_file = tmp_path / "test.docx"
    rfq_file.write_bytes(b"fake content")

    task = RFQTask(
        file_name="test.docx",
        file_path=str(rfq_file),
        processing_status="failed",
        error_msg="some error",
        progress="20",
        rfq_modules={"project_name": "old"},
    )
    db_session.add(task)
    db_session.commit()

    service = RFQAnalysisService(settings)
    # Mock enqueue_analysis to avoid inline worker
    service.enqueue_analysis = MagicMock()

    updated = service.retry_task(db_session, task)

    assert updated.processing_status == "queued"
    assert updated.error_msg is None
    assert updated.progress == "0"
    assert updated.rfq_modules is None
    assert updated.comparison_table is None
    service.enqueue_analysis.assert_called_once()


def test_retry_task_raises_if_file_missing(db_session, settings):
    task = RFQTask(
        file_name="gone.docx",
        file_path="/nonexistent/gone.docx",
        processing_status="failed",
    )
    db_session.add(task)
    db_session.commit()

    service = RFQAnalysisService(settings)
    with pytest.raises(ValueError, match="原始 RFQ 文件已丢失"):
        service.retry_task(db_session, task)


# ─── Stale recovery respects max_attempts ──────────────────────────────────────


def test_recover_stale_jobs_requeues_when_attempts_below_max(db_session, settings):
    task = RFQTask(
        file_name="stale.docx",
        file_path="/tmp/stale.docx",
        processing_status="parsing",
        progress="30",
    )
    db_session.add(task)
    db_session.commit()

    job = TaskJob(
        job_type="rfq_analysis",
        ref_id=task.id,
        status="running",
        attempts=1,
        max_attempts=3,
        started_at=datetime.now(timezone.utc) - timedelta(minutes=20),
    )
    TaskJobRepository(db_session).create(job)

    worker = WorkerService(settings)
    recovered = worker.recover_stale_jobs(db_session)

    assert recovered == 1
    db_session.refresh(job)
    # attempts=1 < max_attempts=3, so job should be re-queued
    assert job.status == "queued"
    db_session.refresh(task)
    # task should also reflect re-queued state
    assert task.processing_status == "queued"
    assert task.error_msg is None


def test_recover_stale_jobs_marks_failed_when_max_attempts_reached(db_session, settings):
    task = RFQTask(
        file_name="stale_final.docx",
        file_path="/tmp/stale_final.docx",
        processing_status="parsing",
        progress="30",
    )
    db_session.add(task)
    db_session.commit()

    job = TaskJob(
        job_type="rfq_analysis",
        ref_id=task.id,
        status="running",
        attempts=3,
        max_attempts=3,
        started_at=datetime.now(timezone.utc) - timedelta(minutes=20),
    )
    TaskJobRepository(db_session).create(job)

    worker = WorkerService(settings)
    recovered = worker.recover_stale_jobs(db_session)

    assert recovered == 1
    db_session.refresh(job)
    assert job.status == "failed"
    db_session.refresh(task)
    assert task.processing_status == "failed"
    assert "超时" in (task.error_msg or "")


# ─── Queue size cap ─────────────────────────────────────────────────────────────


def test_task_max_queue_size_config():
    s = Settings(database_url="sqlite://", task_max_queue_size=10)
    assert s.task_max_queue_size == 10


def test_task_max_queue_size_default():
    s = Settings(database_url="sqlite://")
    assert s.task_max_queue_size == 20
