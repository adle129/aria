from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.knowledge_import import KnowledgeImport
from app.models.task_job import TaskJob
from app.services.knowledge_import_service import KnowledgeImportService


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        bind=engine,
        tables=[TaskJob.__table__, KnowledgeImport.__table__],
    )
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def test_create_and_finish_import_batch(db_session):
    now = datetime.now(timezone.utc)
    job = TaskJob(
        id="job-1",
        job_type="kb_index",
        ref_id="production",
        status="queued",
        payload={
            "mode": "incremental",
            "batch_id": "batch-a",
            "triggered_by": "admin-1",
        },
        queued_at=now,
        created_at=now,
        updated_at=now,
    )
    db_session.add(job)
    db_session.commit()

    service = KnowledgeImportService(db_session)
    record = service.create_for_job(job)
    assert record.job_id == "job-1"
    assert record.mode == "incremental"
    assert record.status == "queued"

    job.status = "completed"
    job.finished_at = now
    service.sync_job_finished(
        job,
        result={
            "new_documents": 2,
            "new_chunks": 10,
            "skipped": 1,
            "failed_files": [{"path": "bad", "error": "rfq missing"}],
            "engagements": [{"engagement_id": "demo", "status": "indexed"}],
        },
    )
    finished = service.get(record.id)
    assert finished.new_chunks == 10
    assert finished.skipped == 1
    assert finished.failed_count == 1
    assert finished.engagements[0]["engagement_id"] == "demo"
