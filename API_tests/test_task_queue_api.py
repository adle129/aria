from datetime import datetime, timedelta, timezone

from app.database import get_db
from app.main import app
from app.models.rfq_task import RFQTask
from app.models.task_job import TaskJob
from app.repositories.rfq_task_repository import RFQTaskRepository
from app.repositories.task_job_repository import TaskJobRepository


def test_upload_creates_queued_task(client, sample_rfq_bytes):
    response = client.post(
        "/api/v1/rfq/upload",
        files={
            "file": (
                "mock_chassis_rfq.docx",
                sample_rfq_bytes,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )
    assert response.status_code == 200
    task_id = response.json()["data"]["task_id"]
    status = client.get(f"/api/v1/rfq/tasks/{task_id}/status").json()
    assert status["status"] in {"dimension_review", "completed", "queued", "parsing", "failed"}
    assert "queue_position" in status
    assert "estimated_wait_seconds" in status
    assert "queue_wait_ms" in status
    assert "run_ms" in status


def test_upload_inline_worker_completes(client, sample_rfq_bytes):
    upload = client.post(
        "/api/v1/rfq/upload",
        files={
            "file": (
                "mock_chassis_rfq.docx",
                sample_rfq_bytes,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )
    task_id = upload.json()["data"]["task_id"]
    status = client.get(f"/api/v1/rfq/tasks/{task_id}/status").json()
    assert status["status"] == "dimension_review"
    assert status["queue_position"] is None
    assert status["queue_wait_ms"] is not None
    assert status["run_ms"] is not None
    assert status["queued_at"] is not None
    assert status["started_at"] is not None
    assert status["finished_at"] is not None
    assert status.get("phase") == "dimension_review"

    detail = client.get(f"/api/v1/rfq/tasks/{task_id}").json()["data"]
    assert detail["queue_wait_ms"] is not None
    assert detail["run_ms"] is not None


def test_status_timing_from_job_timestamps(client, monkeypatch):
    import app.api.v1.rfq as rfq_module

    monkeypatch.setattr(rfq_module.analysis_service.job_service, "uses_inline_worker", lambda: False)
    db = next(app.dependency_overrides[get_db]())
    try:
        task = RFQTask(
            file_name="timing.docx",
            file_path="/tmp/timing.docx",
            processing_status="parsing",
            progress="20",
            status_message="解析中",
        )
        RFQTaskRepository(db).create(task)
        t0 = datetime.now(timezone.utc) - timedelta(seconds=40)
        job = TaskJob(
            job_type="rfq_analysis",
            ref_id=task.id,
            status="running",
            phase="parsing",
            queued_at=t0,
            started_at=t0 + timedelta(seconds=10),
            created_at=t0,
            updated_at=t0,
        )
        TaskJobRepository(db).create(job)
        task_id = task.id
    finally:
        db.close()

    status = client.get(f"/api/v1/rfq/tasks/{task_id}/status").json()
    assert status["status"] == "parsing"
    assert status["phase"] == "parsing"
    assert status["queue_wait_ms"] == 10000
    assert status["run_ms"] is not None
    assert status["run_ms"] >= 25000


def test_knowledge_search_includes_insufficient_evidence(client):
    response = client.post("/api/v1/knowledge/search", json={"query": "MEB chassis", "top_k": 3})
    assert response.status_code == 200
    data = response.json()["data"]
    assert "insufficient_evidence" in data
    assert data["insufficient_evidence"] is False
