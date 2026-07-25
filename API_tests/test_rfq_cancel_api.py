"""API tests: POST /rfq/tasks/{id}/cancel — status codes and response body content."""

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


def _assert_status_payload(data: dict, *, status: str, message_contains: str | list[str], progress: int | None = None):
    assert "status" in data
    assert "progress" in data
    assert "message" in data
    assert data["status"] == status
    message = data.get("message") or ""
    needles = [message_contains] if isinstance(message_contains, str) else message_contains
    for needle in needles:
        assert needle in message, f"expected {needle!r} in message={message!r}"
    if progress is not None:
        assert data["progress"] == progress


def test_cancel_queued_task_returns_cancelled(client):
    db = _db(client)
    task = _make_task(db, processing_status="queued")
    job = TaskJob(job_type="rfq_analysis", ref_id=task.id, status="queued")
    TaskJobRepository(db).create(job)
    db.close()

    resp = client.post(f"/api/v1/rfq/tasks/{task.id}/cancel")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    _assert_status_payload(
        body["data"],
        status="cancelled",
        message_contains="分析已取消",
        progress=0,
    )


def test_cancel_running_task_returns_cancelling(client):
    db = _db(client)
    task = _make_task(db, processing_status="parsing", progress="20")
    job = TaskJob(
        job_type="rfq_analysis",
        ref_id=task.id,
        status="running",
        phase="parsing",
        started_at=datetime.now(timezone.utc),
    )
    TaskJobRepository(db).create(job)
    db.close()

    resp = client.post(f"/api/v1/rfq/tasks/{task.id}/cancel")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    data = body["data"]
    _assert_status_payload(
        data,
        status="cancelling",
        message_contains=["正在取消分析", "模型调用结束后停止"],
        progress=20,
    )
    assert data.get("phase") == "parsing"


def test_cancel_phase2_retrieving(client):
    db = _db(client)
    task = _make_task(
        db,
        processing_status="retrieving",
        progress="55",
        rfq_modules={"project_name": "P"},
        dimension_draft={"items": []},
    )
    db.close()

    resp = client.post(f"/api/v1/rfq/tasks/{task.id}/cancel")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    _assert_status_payload(
        body["data"],
        status="cancelling",
        message_contains=["正在取消矩阵生成", "模型调用结束后停止"],
        progress=55,
    )


def test_cancel_confirm_queued_rolls_back_to_dimension_review(client):
    db = _db(client)
    task = _make_task(
        db,
        processing_status="queued",
        progress="45",
        status_message="对比表任务排队中",
        rfq_modules={"project_name": "P"},
        dimension_draft={
            "items": [{"dimension_id": "d1", "name": "A", "in_scope": True}],
            "custom_items": [],
        },
    )
    job = TaskJob(
        job_type="rfq_confirm",
        ref_id=task.id,
        status="queued",
        phase="queued",
        single_flight_key=f"rfq_confirm:{task.id}",
        payload={"task_id": task.id, "draft_fingerprint": "abc"},
    )
    TaskJobRepository(db).create(job)
    db.close()

    resp = client.post(f"/api/v1/rfq/tasks/{task.id}/cancel")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    data = body["data"]
    _assert_status_payload(
        data,
        status="dimension_review",
        message_contains=["矩阵生成已取消", "维度勾选已保留", "重新确认"],
        progress=40,
    )
    assert data.get("phase") == "dimension_review"

    db = _db(client)
    reloaded = RFQTaskRepository(db).get_by_id(task.id)
    assert reloaded is not None
    assert reloaded.processing_status == "dimension_review"
    assert reloaded.dimension_draft is not None
    assert reloaded.rfq_modules is not None
    assert reloaded.status_message and "重新确认" in reloaded.status_message
    job_row = TaskJobRepository(db).get_by_id(job.id)
    assert job_row is not None
    assert job_row.status == "cancelled"
    db.close()


def test_cancel_confirm_running_returns_cancelling(client):
    db = _db(client)
    task = _make_task(
        db,
        processing_status="retrieving",
        progress="55",
        rfq_modules={"project_name": "P"},
        dimension_draft={
            "items": [{"dimension_id": "d1", "name": "A", "in_scope": True}],
        },
    )
    job = TaskJob(
        job_type="rfq_confirm",
        ref_id=task.id,
        status="running",
        phase="retrieving",
        single_flight_key=f"rfq_confirm:{task.id}",
        started_at=datetime.now(timezone.utc),
        heartbeat_at=datetime.now(timezone.utc),
    )
    TaskJobRepository(db).create(job)
    db.close()

    resp = client.post(f"/api/v1/rfq/tasks/{task.id}/cancel")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    data = body["data"]
    _assert_status_payload(
        data,
        status="cancelling",
        message_contains=["正在取消矩阵生成", "模型调用结束后停止"],
        progress=55,
    )
    assert data.get("phase") == "retrieving"

    db = _db(client)
    job_row = TaskJobRepository(db).get_by_id(job.id)
    assert job_row is not None
    assert job_row.cancel_requested_at is not None
    assert job_row.status == "running"
    task_row = RFQTaskRepository(db).get_by_id(task.id)
    assert task_row is not None
    assert task_row.processing_status == "cancelling"
    assert "取消矩阵" in (task_row.status_message or "")
    db.close()


def test_cancel_idempotent_for_completed(client):
    db = _db(client)
    task = _make_task(
        db,
        processing_status="completed",
        progress="100",
        status_message="分析完成",
    )
    db.close()

    resp = client.post(f"/api/v1/rfq/tasks/{task.id}/cancel")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    _assert_status_payload(
        body["data"],
        status="completed",
        message_contains="分析完成",
        progress=100,
    )


def test_cancel_dimension_review_is_noop(client):
    db = _db(client)
    task = _make_task(
        db,
        processing_status="dimension_review",
        progress="40",
        status_message="等待工程师确认基准维度清单",
        rfq_modules={"project_name": "P"},
        dimension_draft={"items": []},
    )
    db.close()

    resp = client.post(f"/api/v1/rfq/tasks/{task.id}/cancel")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    data = body["data"]
    _assert_status_payload(
        data,
        status="dimension_review",
        message_contains="等待工程师确认基准维度清单",
        progress=40,
    )
    assert data.get("phase") == "dimension_review"


def test_cancel_running_then_status_stays_cancelling(client):
    db = _db(client)
    task = _make_task(db, processing_status="parsing", progress="20")
    job = TaskJob(
        job_type="rfq_analysis",
        ref_id=task.id,
        status="running",
        phase="parsing",
        started_at=datetime.now(timezone.utc),
    )
    TaskJobRepository(db).create(job)
    task_id = task.id
    db.close()

    cancel_resp = client.post(f"/api/v1/rfq/tasks/{task_id}/cancel")
    assert cancel_resp.status_code == 200
    cancel_body = cancel_resp.json()
    assert cancel_body["code"] == 200
    _assert_status_payload(
        cancel_body["data"],
        status="cancelling",
        message_contains=["正在取消分析", "模型调用结束后停止"],
    )

    status_resp = client.get(f"/api/v1/rfq/tasks/{task_id}/status")
    assert status_resp.status_code == 200
    status = status_resp.json()
    assert status["status"] == "cancelling"
    assert "正在取消分析" in (status.get("message") or "")
    assert "模型调用结束后停止" in (status.get("message") or "")
    assert status["progress"] == 20
    assert status.get("phase") == "parsing"


def test_cancel_unknown_task_404(client):
    resp = client.post("/api/v1/rfq/tasks/nonexistent/cancel")
    assert resp.status_code == 404
    body = resp.json()
    assert body["code"] == 404
    assert body["msg"] == "任务 ID 不存在"


def test_delete_in_progress_requires_cancel_first(client):
    db = _db(client)
    task = _make_task(db, processing_status="parsing")
    db.close()

    resp = client.delete(f"/api/v1/rfq/tasks/{task.id}")
    assert resp.status_code == 409
    body = resp.json()
    assert body["code"] == 409
    assert body["msg"] == "进行中的任务不可删除，请先取消分析或等待处理完成"


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
    task = _make_task(
        db,
        processing_status="cancelled",
        file_path=str(stable),
        status_message="分析已取消",
    )
    db.close()

    resp = client.post(f"/api/v1/rfq/tasks/{task.id}/retry")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    data = body["data"]
    assert data["status"] == "queued"
    assert "message" in data
    assert data["status"] != "cancelled"
