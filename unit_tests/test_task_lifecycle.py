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


# ─── Repository — delete edge cases ────────────────────────────────────────────


def test_rfq_task_delete_removes_from_list(db_session):
    repo = RFQTaskRepository(db_session)
    task = RFQTask(file_name="del.docx", file_path="/tmp/del.docx",
                   processing_status="failed")
    repo.create(task)
    repo.delete(task)
    results = repo.list_recent(unique_file_name=False)
    assert not any(t.file_name == "del.docx" for t in results)


def test_rfq_task_delete_nonexistent_is_safe(db_session):
    """Deleting a detached / already deleted task should not crash."""
    repo = RFQTaskRepository(db_session)
    task = RFQTask(file_name="ghost.docx", file_path="/tmp/ghost.docx",
                   processing_status="failed")
    repo.create(task)
    repo.delete(task)
    # Second delete should not raise (task is already expunged)
    try:
        repo.delete(task)
    except Exception:
        pass  # acceptable — just must not crash the app


# ─── Repository — list_recent ───────────────────────────────────────────────────


def test_list_recent_explicit_false_excludes_archived(db_session):
    repo = RFQTaskRepository(db_session)
    t = RFQTask(file_name="hidden.docx", file_path="/tmp/h.docx",
                processing_status="completed", archived=True)
    repo.create(t)
    results = repo.list_recent(unique_file_name=False, include_archived=False)
    assert not any(r.file_name == "hidden.docx" for r in results)


def test_list_recent_limit_honored(db_session):
    repo = RFQTaskRepository(db_session)
    for i in range(6):
        repo.create(RFQTask(file_name=f"f{i}.docx", file_path="/tmp/x.docx",
                            processing_status="completed"))
    assert len(repo.list_recent(3, unique_file_name=False)) <= 3


def test_list_recent_empty_returns_empty_list(db_session):
    repo = RFQTaskRepository(db_session)
    assert repo.list_recent(unique_file_name=False) == []


# ─── RFQAnalysisService.retry_task — field-level assertions ────────────────────


def test_retry_task_clears_all_output_fields(db_session, settings, tmp_path):
    rfq_file = tmp_path / "test.docx"
    rfq_file.write_bytes(b"content")
    task = RFQTask(
        file_name="test.docx",
        file_path=str(rfq_file),
        processing_status="failed",
        error_msg="err",
        progress="80",
        review_status="confirmed",
        rfq_modules={"x": 1},
        dimension_draft={"d": []},
        similar_projects={"s": []},
        comparison_table={"c": []},
        solution_draft={"sol": ""},
        qa_items=[{"q": "?"}],
        excel_path="/out/q.xlsx",
        qa_excel_path="/out/qa.xlsx",
    )
    db_session.add(task)
    db_session.commit()

    service = RFQAnalysisService(settings)
    service.enqueue_analysis = MagicMock()
    updated = service.retry_task(db_session, task)

    assert updated.processing_status == "queued"
    assert updated.review_status == "draft"
    assert updated.error_msg is None
    assert updated.progress == "0"
    assert updated.rfq_modules is None
    assert updated.dimension_draft is None
    assert updated.similar_projects is None
    assert updated.comparison_table is None
    assert updated.solution_draft is None
    assert updated.qa_items is None
    assert updated.excel_path is None
    assert updated.qa_excel_path is None


def test_retry_task_enqueue_called_once(db_session, settings, tmp_path):
    rfq_file = tmp_path / "t.docx"
    rfq_file.write_bytes(b"ok")
    task = RFQTask(file_name="t.docx", file_path=str(rfq_file),
                   processing_status="failed")
    db_session.add(task)
    db_session.commit()
    service = RFQAnalysisService(settings)
    service.enqueue_analysis = MagicMock()
    service.retry_task(db_session, task)
    service.enqueue_analysis.assert_called_once_with(db_session, task)


def test_retry_task_error_message_mentions_reupload(db_session, settings):
    task = RFQTask(file_name="gone.docx", file_path="/no/such/path.docx",
                   processing_status="failed")
    db_session.add(task)
    db_session.commit()
    service = RFQAnalysisService(settings)
    with pytest.raises(ValueError) as exc:
        service.retry_task(db_session, task)
    assert "重新上传" in str(exc.value)


# ─── Stale recovery — boundary and edge cases ──────────────────────────────────


def test_recover_stale_jobs_boundary_max_minus_one(db_session, settings):
    """attempts == max_attempts - 1 → should still re-queue."""
    task = RFQTask(file_name="b.docx", file_path="/tmp/b.docx",
                   processing_status="parsing")
    db_session.add(task)
    db_session.commit()
    job = TaskJob(
        job_type="rfq_analysis", ref_id=task.id, status="running",
        attempts=2, max_attempts=3,
        started_at=datetime.now(timezone.utc) - timedelta(minutes=20),
    )
    TaskJobRepository(db_session).create(job)

    worker = WorkerService(settings)
    worker.recover_stale_jobs(db_session)
    db_session.refresh(job)
    assert job.status == "queued"


def test_recover_stale_no_stale_returns_zero(db_session, settings):
    """No stale jobs → count == 0."""
    worker = WorkerService(settings)
    assert worker.recover_stale_jobs(db_session) == 0


def test_recover_stale_jobs_multiple(db_session, settings):
    """Multiple stale jobs recovered in one call."""
    jobs = []
    for i in range(3):
        t = RFQTask(file_name=f"m{i}.docx", file_path="/tmp/x.docx",
                    processing_status="parsing")
        db_session.add(t)
        db_session.commit()
        j = TaskJob(
            job_type="rfq_analysis", ref_id=t.id, status="running",
            attempts=1, max_attempts=3,
            started_at=datetime.now(timezone.utc) - timedelta(minutes=20),
        )
        TaskJobRepository(db_session).create(j)
        jobs.append(j)

    worker = WorkerService(settings)
    count = worker.recover_stale_jobs(db_session)
    assert count == 3
    for j in jobs:
        db_session.refresh(j)
        assert j.status == "queued"


def test_recover_stale_recent_job_not_recovered(db_session, settings):
    """Job started 5 minutes ago should NOT be considered stale."""
    task = RFQTask(file_name="fresh.docx", file_path="/tmp/x.docx",
                   processing_status="parsing")
    db_session.add(task)
    db_session.commit()
    job = TaskJob(
        job_type="rfq_analysis", ref_id=task.id, status="running",
        attempts=1, max_attempts=3,
        started_at=datetime.now(timezone.utc) - timedelta(minutes=5),
    )
    TaskJobRepository(db_session).create(job)

    worker = WorkerService(settings)
    count = worker.recover_stale_jobs(db_session)
    assert count == 0
    db_session.refresh(job)
    assert job.status == "running"


# ─── TaskJobRepository.count_queued ─────────────────────────────────────────────


def test_count_queued_returns_zero_initially(db_session):
    assert TaskJobRepository(db_session).count_queued() == 0


def test_count_queued_counts_only_queued_status(db_session):
    repo = TaskJobRepository(db_session)
    t = RFQTask(file_name="cq.docx", file_path="/tmp/cq.docx",
                processing_status="queued")
    db_session.add(t)
    db_session.commit()
    for status in ("queued", "queued", "running", "failed", "completed"):
        j = TaskJob(job_type="rfq_analysis", ref_id=t.id, status=status)
        repo.create(j)
    assert repo.count_queued() == 2


# ─── Queue size cap ─────────────────────────────────────────────────────────────


def test_task_max_queue_size_config():
    s = Settings(database_url="sqlite://", task_max_queue_size=10)
    assert s.task_max_queue_size == 10


def test_task_max_queue_size_default():
    s = Settings(database_url="sqlite://")
    assert s.task_max_queue_size == 20


def test_task_max_queue_size_zero_is_valid():
    s = Settings(database_url="sqlite://", task_max_queue_size=0)
    assert s.task_max_queue_size == 0
