from datetime import datetime
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.database import Base
from app.models.rfq_task import RFQTask
from app.models.task_job import TaskJob
from app.repositories.task_job_repository import TaskJobRepository
from app.services.worker_service import WorkerService


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine, tables=[RFQTask.__table__, TaskJob.__table__])
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def test_process_one_completes_rfq_job(db_session, monkeypatch):
    task = RFQTask(
        file_name="a.docx",
        file_path="/tmp/a.docx",
        processing_status="queued",
    )
    db_session.add(task)
    db_session.commit()

    job = TaskJob(
        job_type="rfq_analysis",
        ref_id=task.id,
        status="queued",
    )
    TaskJobRepository(db_session).create(job)

    worker = WorkerService(Settings(database_url="sqlite://", mock_llm=True, mock_rag=True))
    monkeypatch.setattr(worker.analysis_service, "analyze_task", MagicMock())
    processed = worker.process_one(db_session)
    assert processed is not None
    assert processed.status == "completed"


def test_process_one_marks_failed_when_handler_raises(db_session, monkeypatch):
    task = RFQTask(
        file_name="a.docx",
        file_path="/tmp/a.docx",
        processing_status="queued",
    )
    db_session.add(task)
    db_session.commit()

    job = TaskJob(
        job_type="rfq_analysis",
        ref_id=task.id,
        status="queued",
        max_attempts=1,
    )
    TaskJobRepository(db_session).create(job)

    worker = WorkerService(Settings(database_url="sqlite://"))
    monkeypatch.setattr(
        worker.analysis_service,
        "analyze_task",
        MagicMock(side_effect=RuntimeError("parse failed")),
    )
    processed = worker.process_one(db_session)
    assert processed is not None
    assert processed.status == "failed"
    assert "parse failed" in (processed.error_message or "")


def test_recover_stale_jobs_marks_failed(db_session):
    from datetime import timedelta, timezone

    task = RFQTask(
        file_name="stale.docx",
        file_path="/tmp/stale.docx",
        processing_status="parsing",
        progress="40",
        status_message="正在匹配基准维度库（1/1）...",
    )
    db_session.add(task)
    db_session.commit()

    stale = TaskJob(
        job_type="rfq_analysis",
        ref_id=task.id,
        status="running",
        started_at=datetime.now(timezone.utc) - timedelta(minutes=20),
    )
    TaskJobRepository(db_session).create(stale)

    worker = WorkerService(Settings(database_url="sqlite://", task_job_stale_seconds=900))
    reset = worker.recover_stale_jobs(db_session)
    assert reset == 1
    reloaded_job = TaskJobRepository(db_session).get_by_id(stale.id)
    assert reloaded_job.status == "failed"
    db_session.refresh(task)
    assert task.processing_status == "failed"
    assert "超时" in (task.error_msg or "")
