from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.database import Base
from app.models.task_job import TaskJob
from app.repositories.task_job_repository import TaskJobRepository
from app.services.knowledge_index_job_service import KnowledgeIndexJobService


def _session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine, tables=[TaskJob.__table__])
    return sessionmaker(bind=engine)()


def _service() -> KnowledgeIndexJobService:
    return KnowledgeIndexJobService(
        Settings(
            database_url="sqlite://",
            knowledge_vector_namespace="production",
        )
    )


def test_enqueue_reuses_active_single_flight_job():
    db = _session()
    service = _service()
    try:
        first, first_reused = service.enqueue(
            db,
            mode="full",
            triggered_by="admin-1",
        )
        second, second_reused = service.enqueue(
            db,
            mode="full",
            triggered_by="admin-2",
        )

        assert first_reused is False
        assert second_reused is True
        assert second.id == first.id
        assert first.single_flight_key == "kb_index:production"
    finally:
        db.close()


def test_cancel_queued_job_is_immediately_terminal():
    db = _session()
    service = _service()
    try:
        job, _ = service.enqueue(db, mode="full", triggered_by=None)
        cancelled = service.cancel(db, job)

        assert cancelled.status == "cancelled"
        assert cancelled.cancel_requested_at is not None
        assert cancelled.finished_at is not None
    finally:
        db.close()


def test_serialize_running_cancel_request_as_cancelling():
    db = _session()
    service = _service()
    try:
        now = datetime.now(timezone.utc)
        job = TaskJob(
            job_type="kb_index",
            ref_id="production",
            status="running",
            phase="embedding",
            single_flight_key="kb_index:production",
            progress_current=2,
            progress_total=4,
            cancel_requested_at=now,
            created_at=now,
            queued_at=now,
            updated_at=now,
        )
        TaskJobRepository(db).create(job)

        data = service.serialize(db, job)

        assert data["status"] == "cancelling"
        assert data["progress"] == 50
    finally:
        db.close()


def test_completed_job_no_longer_blocks_new_job():
    db = _session()
    service = _service()
    try:
        first, _ = service.enqueue(db, mode="full", triggered_by=None)
        service.jobs.mark_completed(db, first, {"new_chunks": 12})
        second, reused = service.enqueue(db, mode="incremental", triggered_by=None)

        assert reused is False
        assert second.id != first.id
    finally:
        db.close()
