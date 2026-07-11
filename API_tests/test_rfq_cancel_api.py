"""API tests: POST /rfq/tasks/{id}/cancel."""

from datetime import datetime, timezone

from app.database import get_db
from app.main import app
from app.models.rfq_task import RFQTask
from app.models.task_job import TaskJob
from app.repositories.rfq_task_repository import RFQTaskRepository
from app.repositories.task_job_repository import TaskJobRepository


def _db(client):
    return next(app.dependency_overrides[get_db]())


def _make_task(db, *, processing_status="queued", **kwargs):
    task = RFQTask(
        file_name=kwargs.pop("file_name", "cancel_test.docx"),
        file_path=kwargs.pop("file_path", "/tmp/cancel_test.docx"),
        processing_status=processing_status,
        **kwargs,
    )
    RFQTaskRepository(db).create(task)
    db.close()
    return task


def test_cancel_queued_task_returns_cancelled(client):
    db = _db(client)
    task = _make_task(db, processing_status="queued")
    job = TaskJob(job_type="rfq_analysis", ref_id=task.id, status="queued")
    TaskJobRepository(db).create(job)
    db.close()

    resp = client.post(f"/api/v1/rfq/tasks/{task.id}/cancel")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "cancelled"


def test_cancel_running_task_returns_cancelling(client):
    db = _db(client)
    task = _make_task(db, processing_status="parsing")
    job = TaskJob(
        job_type="rfq_analysis",
        ref_id=task.id,
        status="running",
        started_at=datetime.now(timezone.utc),
    )
    TaskJobRepository(db).create(job)
    db.close()

    resp = client.post(f"/api/v1/rfq/tasks/{task.id}/cancel")
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "cancelling"


def test_cancel_phase2_retrieving(client):
    db = _db(client)
    task = _make_task(
        db,
        processing_status="retrieving",
        rfq_modules={"project_name": "P"},
        dimension_draft={"items": []},
    )
    db.close()

    resp = client.post(f"/api/v1/rfq/tasks/{task.id}/cancel")
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "cancelling"


def test_cancel_idempotent_for_completed(client):
    db = _db(client)
    task = _make_task(db, processing_status="completed")
    db.close()

    resp = client.post(f"/api/v1/rfq/tasks/{task.id}/cancel")
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "completed"


def test_cancel_unknown_task_404(client):
    resp = client.post("/api/v1/rfq/tasks/nonexistent/cancel")
    assert resp.status_code == 404


def test_delete_in_progress_requires_cancel_first(client):
    db = _db(client)
    task = _make_task(db, processing_status="parsing")
    db.close()

    resp = client.delete(f"/api/v1/rfq/tasks/{task.id}")
    assert resp.status_code == 409


def test_retry_cancelled_task(client, upload_dir, monkeypatch):
    import app.api.v1.rfq as rfq_module

    stable = upload_dir / "uploads" / "cancel_retry.docx"
    stable.parent.mkdir(parents=True, exist_ok=True)
    stable.write_bytes(b"fake-docx")

    monkeypatch.setattr(
        rfq_module.analysis_service.job_service,
        "uses_inline_worker",
        lambda: False,
    )

    db = _db(client)
    task = _make_task(db, processing_status="cancelled", file_path=str(stable))
    db.close()

    resp = client.post(f"/api/v1/rfq/tasks/{task.id}/retry")
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "queued"
