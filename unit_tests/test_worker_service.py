from datetime import datetime
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.database import Base
from app.models.knowledge_import import KnowledgeImport
from app.models.rfq_task import RFQTask
from app.models.task_job import TaskJob
from app.repositories.task_job_repository import TaskJobRepository
from app.services.engagement_ingest_service import EngagementIngestCancelled
from app.services.rfq_analysis_service import RFQAnalysisCancelled
from app.services.knowledge_index_job_service import KnowledgeIndexJobService
from app.services.worker_service import WorkerService


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        bind=engine,
        tables=[RFQTask.__table__, TaskJob.__table__, KnowledgeImport.__table__],
    )
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


def test_process_one_completes_kb_index_job(db_session, monkeypatch):
    job = TaskJob(
        job_type="kb_index",
        ref_id="production",
        status="queued",
        max_attempts=1,
    )
    TaskJobRepository(db_session).create(job)
    monkeypatch.setattr(
        KnowledgeIndexJobService,
        "execute",
        MagicMock(return_value={"new_chunks": 42}),
    )

    processed = WorkerService(Settings(database_url="sqlite://")).process_one(db_session)

    assert processed is not None
    assert processed.status == "completed"
    assert processed.result_summary == {"new_chunks": 42}


def test_process_one_cancels_kb_index_at_safe_boundary(db_session, monkeypatch):
    job = TaskJob(
        job_type="kb_index",
        ref_id="production",
        status="queued",
        max_attempts=1,
    )
    TaskJobRepository(db_session).create(job)
    monkeypatch.setattr(
        KnowledgeIndexJobService,
        "execute",
        MagicMock(side_effect=EngagementIngestCancelled()),
    )

    processed = WorkerService(Settings(database_url="sqlite://")).process_one(db_session)

    assert processed is not None
    assert processed.status == "cancelled"


def test_process_one_marks_cancelled_for_rfq_cancel(db_session, monkeypatch):
    task = RFQTask(
        file_name="a.docx",
        file_path="/tmp/a.docx",
        processing_status="parsing",
    )
    db_session.add(task)
    db_session.commit()

    job = TaskJob(
        job_type="rfq_analysis",
        ref_id=task.id,
        status="queued",
    )
    TaskJobRepository(db_session).create(job)

    worker = WorkerService(Settings(database_url="sqlite://"))
    monkeypatch.setattr(
        worker.analysis_service,
        "analyze_task",
        MagicMock(side_effect=RFQAnalysisCancelled()),
    )
    processed = worker.process_one(db_session)
    assert processed is not None
    assert processed.status == "cancelled"
    db_session.refresh(task)
    assert task.processing_status == "cancelled"


def test_recover_stale_jobs_marks_failed_when_max_attempts_reached(db_session):
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

    # attempts == max_attempts → should permanently fail
    stale = TaskJob(
        job_type="rfq_analysis",
        ref_id=task.id,
        status="running",
        attempts=3,
        max_attempts=3,
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


def test_recover_stale_jobs_requeues_when_under_max_attempts(db_session):
    from datetime import timedelta, timezone

    task = RFQTask(
        file_name="stale2.docx",
        file_path="/tmp/stale2.docx",
        processing_status="parsing",
    )
    db_session.add(task)
    db_session.commit()

    # attempts=1 < max_attempts=3 → should re-queue
    stale = TaskJob(
        job_type="rfq_analysis",
        ref_id=task.id,
        status="running",
        attempts=1,
        max_attempts=3,
        started_at=datetime.now(timezone.utc) - timedelta(minutes=20),
    )
    TaskJobRepository(db_session).create(stale)

    worker = WorkerService(Settings(database_url="sqlite://", task_job_stale_seconds=900))
    reset = worker.recover_stale_jobs(db_session)
    assert reset == 1
    reloaded_job = TaskJobRepository(db_session).get_by_id(stale.id)
    assert reloaded_job.status == "queued"
    db_session.refresh(task)
    assert task.processing_status == "queued"
    assert task.error_msg is None


def test_recover_stale_jobs_recovers_orphaned_confirm_phase(db_session):
    from datetime import timedelta, timezone

    task = RFQTask(
        file_name="orphan.docx",
        file_path="/tmp/orphan.docx",
        processing_status="retrieving",
        progress="55",
        status_message="正在检索相似历史项目...",
        rfq_modules={"project_name": "MEB"},
        dimension_draft={"items": [{"in_scope": True, "name": "x"}]},
        updated_at=datetime.now(timezone.utc) - timedelta(minutes=20),
    )
    db_session.add(task)
    db_session.commit()

    worker = WorkerService(Settings(database_url="sqlite://", task_job_stale_seconds=900))
    reset = worker.recover_stale_jobs(db_session)
    assert reset == 1
    db_session.refresh(task)
    assert task.processing_status == "dimension_review"
    assert task.progress == "40"


def test_recover_stale_jobs_honours_cancel_requested(db_session):
    from datetime import timedelta, timezone

    task = RFQTask(
        file_name="cancel_stale.docx",
        file_path="/tmp/cancel_stale.docx",
        processing_status="parsing",
    )
    db_session.add(task)
    db_session.commit()

    stale = TaskJob(
        job_type="rfq_analysis",
        ref_id=task.id,
        status="running",
        attempts=1,
        max_attempts=3,
        started_at=datetime.now(timezone.utc),
        heartbeat_at=datetime.now(timezone.utc),
        cancel_requested_at=datetime.now(timezone.utc) - timedelta(seconds=180),
    )
    TaskJobRepository(db_session).create(stale)

    worker = WorkerService(
        Settings(
            database_url="sqlite://",
            task_job_stale_seconds=900,
            task_job_cancel_stale_seconds=120,
        )
    )
    reset = worker.recover_stale_jobs(db_session)
    assert reset == 1
    reloaded_job = TaskJobRepository(db_session).get_by_id(stale.id)
    assert reloaded_job.status == "cancelled"
    db_session.refresh(task)
    assert task.processing_status == "cancelled"
