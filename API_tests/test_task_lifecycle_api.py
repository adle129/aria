"""API tests: retry, delete, archive, queue limit."""

import time

from app.main import app


def _upload(client, sample_rfq_bytes, filename="test.docx"):
    return client.post(
        "/api/v1/rfq/upload",
        files={"file": (filename, sample_rfq_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )


def test_retry_non_failed_task_returns_400(client, sample_rfq_bytes, monkeypatch):
    import app.api.v1.rfq as rfq_module
    monkeypatch.setattr(rfq_module.analysis_service.job_service, "uses_inline_worker", lambda: False)
    resp = _upload(client, sample_rfq_bytes)
    assert resp.status_code == 200
    task_id = resp.json()["data"]["task_id"]
    retry = client.post(f"/api/v1/rfq/tasks/{task_id}/retry")
    assert retry.status_code == 400
    assert "失败" in retry.json()["msg"]


def test_retry_not_found_returns_404(client):
    assert client.post("/api/v1/rfq/tasks/nonexistent-id/retry").status_code == 404


def test_retry_failed_task_requeues(client, monkeypatch):
    import app.api.v1.rfq as rfq_module
    from app.database import get_db
    from app.models.rfq_task import RFQTask
    from app.repositories.rfq_task_repository import RFQTaskRepository
    db = next(app.dependency_overrides[get_db]())
    task = RFQTask(file_name="fail.docx", file_path=__file__, processing_status="failed", error_msg="boom")
    RFQTaskRepository(db).create(task)
    db.close()
    monkeypatch.setattr(rfq_module.analysis_service.job_service, "uses_inline_worker", lambda: False)
    resp = client.post(f"/api/v1/rfq/tasks/{task.id}/retry")
    assert resp.status_code == 200
    assert resp.json()["code"] == 200
    status = client.get(f"/api/v1/rfq/tasks/{task.id}/status").json()
    assert status["status"] in {"queued", "parsing", "completed", "dimension_review", "failed"}


def test_delete_not_found_returns_404(client):
    assert client.delete("/api/v1/rfq/tasks/nonexistent-id").status_code == 404


def test_delete_in_progress_task_returns_409(client, sample_rfq_bytes, monkeypatch):
    import app.api.v1.rfq as rfq_module
    monkeypatch.setattr(rfq_module.analysis_service.job_service, "uses_inline_worker", lambda: False)
    resp = _upload(client, sample_rfq_bytes)
    assert resp.status_code == 200
    delete_resp = client.delete(f"/api/v1/rfq/tasks/{resp.json()['data']['task_id']}")
    assert delete_resp.status_code == 409
    assert "进行中" in delete_resp.json()["msg"]


def test_delete_failed_task_removes_it(client):
    from app.database import get_db
    from app.models.rfq_task import RFQTask
    from app.repositories.rfq_task_repository import RFQTaskRepository
    db = next(app.dependency_overrides[get_db]())
    task = RFQTask(file_name="deleteme.docx", file_path=__file__, processing_status="failed")
    RFQTaskRepository(db).create(task)
    db.close()
    assert client.delete(f"/api/v1/rfq/tasks/{task.id}").status_code == 204
    assert client.get(f"/api/v1/rfq/tasks/{task.id}").status_code == 404


def test_delete_completed_task_removes_it(client):
    from app.database import get_db
    from app.models.rfq_task import RFQTask
    from app.repositories.rfq_task_repository import RFQTaskRepository
    db = next(app.dependency_overrides[get_db]())
    task = RFQTask(file_name="done.docx", file_path=__file__, processing_status="completed")
    RFQTaskRepository(db).create(task)
    db.close()
    assert client.delete(f"/api/v1/rfq/tasks/{task.id}").status_code == 204


def test_archive_not_found_returns_404(client):
    assert client.patch("/api/v1/rfq/tasks/nonexistent-id/archive").status_code == 404


def test_archive_completed_task_hides_from_list(client):
    from app.database import get_db
    from app.models.rfq_task import RFQTask
    from app.repositories.rfq_task_repository import RFQTaskRepository
    db = next(app.dependency_overrides[get_db]())
    task = RFQTask(file_name="archive_me.docx", file_path=__file__, processing_status="completed")
    RFQTaskRepository(db).create(task)
    db.close()
    assert any(t["task_id"] == task.id for t in client.get("/api/v1/rfq/tasks", params={"unique_file": False}).json()["data"])
    assert client.patch(f"/api/v1/rfq/tasks/{task.id}/archive").json()["code"] == 200
    assert not any(t["task_id"] == task.id for t in client.get("/api/v1/rfq/tasks", params={"unique_file": False}).json()["data"])
    assert any(t["task_id"] == task.id for t in client.get("/api/v1/rfq/tasks", params={"unique_file": False, "include_archived": True}).json()["data"])


def test_archive_in_progress_task_returns_409(client, sample_rfq_bytes, monkeypatch):
    import app.api.v1.rfq as rfq_module
    monkeypatch.setattr(rfq_module.analysis_service.job_service, "uses_inline_worker", lambda: False)
    task_id = _upload(client, sample_rfq_bytes).json()["data"]["task_id"]
    assert client.patch(f"/api/v1/rfq/tasks/{task_id}/archive").status_code == 409


def test_upload_returns_429_when_queue_full(client, sample_rfq_bytes, monkeypatch):
    import app.api.v1.rfq as rfq_module
    from app.config import get_settings
    settings = get_settings()
    monkeypatch.setattr(settings, "task_max_queue_size", 0)
    monkeypatch.setattr(rfq_module.analysis_service.job_service, "uses_inline_worker", lambda: False)
    resp = _upload(client, sample_rfq_bytes)
    assert resp.status_code == 429
    body = resp.json()
    assert body["code"] == 429
    assert "队列" in body["msg"]
    assert "queue_depth" in body


def test_upload_succeeds_when_queue_has_space(client, sample_rfq_bytes, monkeypatch):
    import app.api.v1.rfq as rfq_module
    from app.config import get_settings
    settings = get_settings()
    monkeypatch.setattr(settings, "task_max_queue_size", 100)
    monkeypatch.setattr(rfq_module.analysis_service.job_service, "uses_inline_worker", lambda: False)
    assert _upload(client, sample_rfq_bytes).status_code == 200
