from datetime import datetime, timedelta, timezone
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
from app.services.rfq_analysis_service import (
    RFQAnalysisCancelled,
    RFQAnalysisService,
    RFQ_JOB_PRIORITY,
)


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


def _task(**kwargs) -> RFQTask:
    defaults = {
        "file_name": "a.docx",
        "file_path": "/tmp/a.docx",
        "processing_status": "queued",
    }
    defaults.update(kwargs)
    return RFQTask(**defaults)


def test_enqueue_rfq_job_uses_priority(db_session):
    task = _task()
    db_session.add(task)
    db_session.commit()

    service = RFQAnalysisService(
        Settings(database_url="sqlite://", mock_llm=True, mock_rag=True, task_worker_inline=False)
    )
    service.enqueue_analysis(db_session, task)

    job = TaskJobRepository(db_session).get_active_by_ref("rfq_analysis", task.id)
    assert job is not None
    assert job.priority == RFQ_JOB_PRIORITY


def test_cancel_queued_task_immediately(db_session):
    task = _task(processing_status="queued")
    db_session.add(task)
    db_session.commit()
    job = TaskJob(
        job_type="rfq_analysis",
        ref_id=task.id,
        status="queued",
        priority=RFQ_JOB_PRIORITY,
    )
    TaskJobRepository(db_session).create(job)

    service = RFQAnalysisService(Settings(database_url="sqlite://"))
    updated = service.cancel_task(db_session, task)

    db_session.refresh(job)
    assert job.status == "cancelled"
    assert updated.processing_status == "cancelled"
    assert updated.rfq_modules is None


def test_cancel_running_task_sets_cancelling_status(db_session):
    task = _task(processing_status="parsing", status_message="解析中")
    db_session.add(task)
    db_session.commit()
    job = TaskJob(
        job_type="rfq_analysis",
        ref_id=task.id,
        status="running",
        started_at=datetime.now(timezone.utc),
    )
    TaskJobRepository(db_session).create(job)

    service = RFQAnalysisService(Settings(database_url="sqlite://"))
    service.cancel_task(db_session, task)

    db_session.refresh(job)
    db_session.refresh(task)
    assert job.cancel_requested_at is not None
    assert job.status == "running"
    payload = service.get_status_payload(task, db_session)
    assert payload["status"] == "cancelling"


def test_cancel_phase2_sets_cancelling_on_task(db_session):
    task = _task(
        processing_status="retrieving",
        rfq_modules={"project_name": "P1"},
        dimension_draft={"items": [{"dimension_id": "d1", "in_scope": True}]},
    )
    db_session.add(task)
    db_session.commit()

    service = RFQAnalysisService(Settings(database_url="sqlite://"))
    updated = service.cancel_task(db_session, task)

    assert updated.processing_status == "cancelling"
    payload = service.get_status_payload(updated, db_session)
    assert payload["status"] == "cancelling"


def test_cancel_terminal_states_are_idempotent(db_session):
    task = _task(processing_status="completed")
    db_session.add(task)
    db_session.commit()

    service = RFQAnalysisService(Settings(database_url="sqlite://"))
    updated = service.cancel_task(db_session, task)
    assert updated.processing_status == "completed"


def test_analyze_task_raises_cancel_and_marks_task(db_session, monkeypatch):
    task = _task(processing_status="queued")
    db_session.add(task)
    db_session.commit()
    job = TaskJob(
        job_type="rfq_analysis",
        ref_id=task.id,
        status="running",
        started_at=datetime.now(timezone.utc),
        cancel_requested_at=datetime.now(timezone.utc),
    )
    TaskJobRepository(db_session).create(job)

    service = RFQAnalysisService(Settings(database_url="sqlite://", mock_llm=True, mock_rag=True))
    monkeypatch.setattr(service.parse_service, "parse_rules_first", MagicMock(return_value={"modules": []}))

    with pytest.raises(RFQAnalysisCancelled):
        service.analyze_task(db_session, task.id)

    db_session.refresh(task)
    assert task.processing_status == "cancelled"
    assert task.rfq_modules is None


def test_confirm_dimensions_rolls_back_when_cancelling(db_session, monkeypatch):
    task = _task(
        processing_status="dimension_review",
        rfq_modules={"project_name": "Demo"},
        dimension_draft={
            "items": [{"dimension_id": "d1", "name": "A", "in_scope": True}],
            "custom_items": [],
        },
    )
    db_session.add(task)
    db_session.commit()

    service = RFQAnalysisService(Settings(database_url="sqlite://", mock_llm=True, mock_rag=True))

    def fake_search(*_args, **_kwargs):
        task.processing_status = "cancelling"
        db_session.commit()
        return [{"similarity_score": 0.9, "metadata": {"project_name": "H1"}}]

    monkeypatch.setattr(service.rag, "search_similar_projects", fake_search)

    updated = service.confirm_dimensions(
        db_session,
        task,
        {
            "items": [{"dimension_id": "d1", "in_scope": True}],
            "custom_items": [],
        },
    ).task

    assert updated.processing_status == "dimension_review"
    assert updated.comparison_table is None
    assert updated.similar_projects is None
    assert "重新确认" in (updated.status_message or "")


def test_job_cancel_check_is_throttled(db_session, monkeypatch):
    task = _task(processing_status="parsing")
    db_session.add(task)
    db_session.commit()
    job = TaskJob(
        job_type="rfq_analysis",
        ref_id=task.id,
        status="running",
        started_at=datetime.now(timezone.utc),
    )
    TaskJobRepository(db_session).create(job)

    service = RFQAnalysisService(Settings(database_url="sqlite://"))
    cancel_check = service._make_job_cancel_check(db_session, job.id)
    lookups: list[str] = []
    clock = {"now": 1000.0}

    original_get = TaskJobRepository.get_by_id

    def counting_get(self, job_id):
        lookups.append(job_id)
        return original_get(self, job_id)

    monkeypatch.setattr(TaskJobRepository, "get_by_id", counting_get)
    monkeypatch.setattr(
        "app.services.rfq_analysis_service.time.monotonic",
        lambda: clock["now"],
    )

    for _ in range(5):
        cancel_check()
    assert len(lookups) == 1

    clock["now"] += 0.6
    cancel_check()
    assert len(lookups) == 2


def test_job_cancel_check_sees_cancel_from_other_session(db_session):
    """Worker Session must not keep a stale cancel_requested_at=None."""
    task = _task(processing_status="parsing")
    db_session.add(task)
    db_session.commit()
    job = TaskJob(
        job_type="rfq_analysis",
        ref_id=task.id,
        status="running",
        started_at=datetime.now(timezone.utc),
    )
    TaskJobRepository(db_session).create(job)

    # Load into identity map as the worker would.
    assert db_session.get(TaskJob, job.id).cancel_requested_at is None

    other = sessionmaker(bind=db_session.get_bind())()
    try:
        other_job = other.get(TaskJob, job.id)
        assert other_job is not None
        other_job.cancel_requested_at = datetime.now(timezone.utc)
        other.commit()
    finally:
        other.close()

    service = RFQAnalysisService(Settings(database_url="sqlite://"))
    cancel_check = service._make_job_cancel_check(db_session, job.id)
    with pytest.raises(RFQAnalysisCancelled):
        cancel_check()


def test_task_cancel_check_sees_cancelling_from_other_session(db_session):
    task = _task(processing_status="retrieving")
    db_session.add(task)
    db_session.commit()
    assert db_session.get(RFQTask, task.id).processing_status == "retrieving"

    other = sessionmaker(bind=db_session.get_bind())()
    try:
        other_task = other.get(RFQTask, task.id)
        assert other_task is not None
        other_task.processing_status = "cancelling"
        other.commit()
    finally:
        other.close()

    service = RFQAnalysisService(Settings(database_url="sqlite://"))
    cancel_check = service._make_task_cancel_check(db_session, task.id)
    with pytest.raises(RFQAnalysisCancelled):
        cancel_check()


def test_analyze_task_honours_cancel_set_during_match(db_session, monkeypatch, tmp_path):
    """Regression: cancel during matching must not finish as dimension_review."""
    rfq_file = tmp_path / "race.docx"
    rfq_file.write_bytes(b"PK")
    task = _task(processing_status="queued", file_path=str(rfq_file))
    db_session.add(task)
    db_session.commit()
    job = TaskJob(
        job_type="rfq_analysis",
        ref_id=task.id,
        status="running",
        started_at=datetime.now(timezone.utc),
    )
    TaskJobRepository(db_session).create(job)
    assert db_session.get(TaskJob, job.id).cancel_requested_at is None

    clock = {"now": 1000.0}
    monkeypatch.setattr(
        "app.services.rfq_analysis_service.time.monotonic",
        lambda: clock["now"],
    )

    service = RFQAnalysisService(
        Settings(database_url="sqlite://", mock_llm=True, mock_rag=True)
    )
    monkeypatch.setattr(
        service.parse_service,
        "parse_rules_first",
        MagicMock(return_value={"modules": [], "project_name": "P"}),
    )

    def fake_match(*_args, cancel_check=None, **_kwargs):
        other = sessionmaker(bind=db_session.get_bind())()
        try:
            other_job = other.get(TaskJob, job.id)
            assert other_job is not None
            other_job.cancel_requested_at = datetime.now(timezone.utc)
            other.commit()
        finally:
            other.close()
        # Bypass cancel_check throttle so the refresh path is exercised.
        clock["now"] += 1.0
        if cancel_check is not None:
            cancel_check()
        return {"items": [], "custom_items": []}

    monkeypatch.setattr(service.dimension_match, "match_rfq_to_baseline", fake_match)

    with pytest.raises(RFQAnalysisCancelled):
        service.analyze_task(db_session, task.id)

    db_session.refresh(task)
    assert task.processing_status == "cancelled"
    assert task.dimension_draft is None


def test_confirm_dimensions_rolls_back_on_embed_cancel(db_session, monkeypatch):
    task = _task(
        processing_status="dimension_review",
        rfq_modules={"project_name": "Demo"},
        dimension_draft={
            "items": [{"dimension_id": "d1", "name": "A", "in_scope": True}],
            "custom_items": [],
        },
    )
    db_session.add(task)
    db_session.commit()

    service = RFQAnalysisService(Settings(database_url="sqlite://", mock_llm=True, mock_rag=True))

    def fake_search(*_args, **kwargs):
        task.processing_status = "cancelling"
        db_session.commit()
        cancel_check = kwargs.get("cancel_check")
        if cancel_check is not None:
            cancel_check()
        return []

    monkeypatch.setattr(service.rag, "search_similar_projects", fake_search)

    updated = service.confirm_dimensions(
        db_session,
        task,
        {
            "items": [{"dimension_id": "d1", "in_scope": True}],
            "custom_items": [],
        },
    ).task

    assert updated.processing_status == "dimension_review"
    assert updated.comparison_table is None


def test_recover_stale_cancelling_returns_to_review(db_session):
    stale = datetime.now(timezone.utc) - timedelta(seconds=3600)
    task = _task(
        processing_status="cancelling",
        updated_at=stale,
        rfq_modules={"project_name": "P"},
        dimension_draft={"items": []},
    )
    db_session.add(task)
    db_session.commit()

    service = RFQAnalysisService(
        Settings(database_url="sqlite://", task_job_stale_seconds=900)
    )
    recovered = service.recover_orphaned_confirm_phase(db_session, task)

    assert recovered.processing_status == "dimension_review"


def test_cancel_confirm_queued_rolls_back_to_review(db_session):
    task = _task(
        processing_status="queued",
        progress="45",
        status_message="对比表任务排队中",
        rfq_modules={"project_name": "Demo"},
        dimension_draft={
            "items": [{"dimension_id": "d1", "name": "A", "in_scope": True}],
            "custom_items": [],
        },
    )
    db_session.add(task)
    db_session.commit()
    job = TaskJob(
        job_type="rfq_confirm",
        ref_id=task.id,
        status="queued",
        phase="queued",
        single_flight_key=f"rfq_confirm:{task.id}",
        payload={"task_id": task.id, "draft_fingerprint": "fp1"},
    )
    TaskJobRepository(db_session).create(job)

    service = RFQAnalysisService(Settings(database_url="sqlite://"))
    updated = service.cancel_task(db_session, task)

    db_session.refresh(job)
    assert job.status == "cancelled"
    assert updated.processing_status == "dimension_review"
    assert updated.rfq_modules is not None
    assert updated.dimension_draft is not None
    assert "重新确认" in (updated.status_message or "")


def test_recover_orphaned_confirm_queued_without_job(db_session):
    stale = datetime.now(timezone.utc) - timedelta(seconds=3600)
    task = _task(
        processing_status="queued",
        progress="45",
        status_message="对比表任务排队中",
        updated_at=stale,
        rfq_modules={"project_name": "P"},
        dimension_draft={"items": [{"dimension_id": "d1", "in_scope": True}]},
    )
    db_session.add(task)
    db_session.commit()

    service = RFQAnalysisService(
        Settings(database_url="sqlite://", task_job_stale_seconds=900)
    )
    recovered = service.recover_orphaned_confirm_phase(db_session, task)

    assert recovered.processing_status == "dimension_review"
    assert "重新确认" in (recovered.status_message or "")


def test_recover_orphaned_skips_phase1_queued(db_session):
    stale = datetime.now(timezone.utc) - timedelta(seconds=3600)
    task = _task(
        processing_status="queued",
        progress="0",
        updated_at=stale,
        rfq_modules=None,
        dimension_draft=None,
    )
    db_session.add(task)
    db_session.commit()
    job = TaskJob(
        job_type="rfq_analysis",
        ref_id=task.id,
        status="queued",
    )
    TaskJobRepository(db_session).create(job)

    service = RFQAnalysisService(
        Settings(database_url="sqlite://", task_job_stale_seconds=900)
    )
    same = service.recover_orphaned_confirm_phase(db_session, task)
    assert same.processing_status == "queued"
