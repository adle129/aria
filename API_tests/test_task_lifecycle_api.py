"""API tests: retry, delete, archive, queue limit.

Coverage:
- Normal flow: retry/delete/archive happy paths
- Boundary: 404 for unknown IDs, 409 for in-progress, 400 for bad state
- Response message content validation
- include_archived parameter (GET /rfq/tasks)
- Queue limit (429 with queue_depth field)
- Integration chains: fail->retry->queued, archive->delete, full lifecycle
"""

import pytest

from app.database import get_db
from app.main import app
from app.models.rfq_task import RFQTask
from app.repositories.rfq_task_repository import RFQTaskRepository

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

from pathlib import Path as _Path

# Disposable stand-in for task.file_path; recreated after delete tests unlink it.
_STABLE_FILE = _Path(__file__).parent / "_test_fixtures" / "stable_rfq.docx"


def _ensure_stable_file() -> str:
    _STABLE_FILE.parent.mkdir(exist_ok=True)
    if not _STABLE_FILE.is_file():
        _STABLE_FILE.write_bytes(b"fake-docx-for-lifecycle-api-tests")
    return str(_STABLE_FILE)


def _db(client):
    return next(app.dependency_overrides[get_db]())


def _make_task(db, *, processing_status="failed", file_path=None, **kwargs):
    task = RFQTask(
        file_name=kwargs.pop("file_name", "test.docx"),
        file_path=file_path if file_path is not None else _ensure_stable_file(),
        processing_status=processing_status,
        **kwargs,
    )
    RFQTaskRepository(db).create(task)
    db.close()
    return task


def _upload(client, sample_rfq_bytes, filename="test.docx"):
    return client.post(
        "/api/v1/rfq/upload",
        files={
            "file": (
                filename,
                sample_rfq_bytes,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )


# ---------------------------------------------------------------------------
# Original smoke tests (preserved for backwards compatibility)
# ---------------------------------------------------------------------------

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
    db = _db(client)
    task = _make_task(db, processing_status="failed", error_msg="boom")
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
    db = _db(client)
    task = _make_task(db, processing_status="failed")
    assert client.delete(f"/api/v1/rfq/tasks/{task.id}").status_code == 204
    assert client.get(f"/api/v1/rfq/tasks/{task.id}").status_code == 404


def test_delete_completed_task_removes_it(client):
    db = _db(client)
    task = _make_task(db, processing_status="completed")
    assert client.delete(f"/api/v1/rfq/tasks/{task.id}").status_code == 204


def test_archive_not_found_returns_404(client):
    assert client.patch("/api/v1/rfq/tasks/nonexistent-id/archive").status_code == 404


def test_archive_completed_task_hides_from_list(client):
    db = _db(client)
    task = _make_task(db, processing_status="completed", file_name="archive_me.docx")
    assert any(
        t["task_id"] == task.id
        for t in client.get("/api/v1/rfq/tasks", params={"unique_file": False}).json()["data"]
    )
    assert client.patch(f"/api/v1/rfq/tasks/{task.id}/archive").json()["code"] == 200
    assert not any(
        t["task_id"] == task.id
        for t in client.get("/api/v1/rfq/tasks", params={"unique_file": False}).json()["data"]
    )
    assert any(
        t["task_id"] == task.id
        for t in client.get(
            "/api/v1/rfq/tasks", params={"unique_file": False, "include_archived": True}
        ).json()["data"]
    )


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


# =============================================================================
# Comprehensive retry endpoint tests
# =============================================================================

class TestRetry:

    def test_unknown_id_returns_404(self, client):
        assert client.post("/api/v1/rfq/tasks/does-not-exist/retry").status_code == 404

    def test_unknown_id_message(self, client):
        assert client.post("/api/v1/rfq/tasks/does-not-exist/retry").json()["msg"] == "任务 ID 不存在"

    @pytest.mark.parametrize(
        "status",
        ["queued", "parsing", "retrieving", "generating", "cancelling", "completed", "dimension_review", "pending"],
    )
    def test_non_failed_status_returns_400(self, client, status):
        db = _db(client)
        task = _make_task(db, processing_status=status)
        assert client.post(f"/api/v1/rfq/tasks/{task.id}/retry").status_code == 400

    def test_non_failed_message_exact(self, client):
        db = _db(client)
        task = _make_task(db, processing_status="completed")
        assert client.post(f"/api/v1/rfq/tasks/{task.id}/retry").json()["msg"] == "只有失败或已取消状态的任务才能重试"

    def test_archived_returns_400(self, client):
        db = _db(client)
        task = _make_task(db, processing_status="failed", archived=True)
        assert client.post(f"/api/v1/rfq/tasks/{task.id}/retry").status_code == 400

    def test_archived_message_exact(self, client):
        db = _db(client)
        task = _make_task(db, processing_status="failed", archived=True)
        assert client.post(f"/api/v1/rfq/tasks/{task.id}/retry").json()["msg"] == "已归档任务不支持重试"

    def test_missing_file_returns_400(self, client):
        db = _db(client)
        task = _make_task(db, processing_status="failed", file_path="/no/such/gone.docx")
        assert client.post(f"/api/v1/rfq/tasks/{task.id}/retry").status_code == 400

    def test_missing_file_message_contains_hint(self, client):
        db = _db(client)
        task = _make_task(db, processing_status="failed", file_path="/no/such/gone.docx")
        assert "文件" in client.post(f"/api/v1/rfq/tasks/{task.id}/retry").json()["msg"]

    def test_success_returns_200(self, client, monkeypatch):
        import app.api.v1.rfq as rfq_module
        monkeypatch.setattr(rfq_module.analysis_service.job_service, "uses_inline_worker", lambda: False)
        db = _db(client)
        task = _make_task(db, processing_status="failed")
        r = client.post(f"/api/v1/rfq/tasks/{task.id}/retry")
        assert r.status_code == 200
        assert r.json()["code"] == 200
        assert "status" in r.json()["data"]

    def test_success_task_is_requeued(self, client, monkeypatch):
        import app.api.v1.rfq as rfq_module
        monkeypatch.setattr(rfq_module.analysis_service.job_service, "uses_inline_worker", lambda: False)
        db = _db(client)
        task = _make_task(db, processing_status="failed", error_msg="old error")
        client.post(f"/api/v1/rfq/tasks/{task.id}/retry")
        status = client.get(f"/api/v1/rfq/tasks/{task.id}/status").json()
        assert status["status"] == "queued"
        assert status["progress"] == 0

    def test_retry_clears_error_msg(self, client, monkeypatch):
        import app.api.v1.rfq as rfq_module
        monkeypatch.setattr(rfq_module.analysis_service.job_service, "uses_inline_worker", lambda: False)
        db = _db(client)
        task = _make_task(db, processing_status="failed", error_msg="previous error")
        client.post(f"/api/v1/rfq/tasks/{task.id}/retry")
        task_data = client.get(f"/api/v1/rfq/tasks/{task.id}").json()["data"]
        assert not task_data.get("error_msg")

    def test_idempotency_second_retry_rejected(self, client, monkeypatch):
        import app.api.v1.rfq as rfq_module
        monkeypatch.setattr(rfq_module.analysis_service.job_service, "uses_inline_worker", lambda: False)
        db = _db(client)
        task = _make_task(db, processing_status="failed")
        assert client.post(f"/api/v1/rfq/tasks/{task.id}/retry").status_code == 200
        r2 = client.post(f"/api/v1/rfq/tasks/{task.id}/retry")
        assert r2.status_code == 400
        assert r2.json()["msg"] == "只有失败或已取消状态的任务才能重试"


# =============================================================================
# Comprehensive delete endpoint tests
# =============================================================================

class TestDeleteComprehensive:

    def test_unknown_id_returns_404(self, client):
        assert client.delete("/api/v1/rfq/tasks/does-not-exist").status_code == 404

    def test_unknown_id_message(self, client):
        assert client.delete("/api/v1/rfq/tasks/does-not-exist").json()["msg"] == "任务 ID 不存在"

    @pytest.mark.parametrize("status", ["queued", "parsing", "retrieving", "generating", "cancelling"])
    def test_in_progress_returns_409(self, client, status):
        db = _db(client)
        task = _make_task(db, processing_status=status)
        r = client.delete(f"/api/v1/rfq/tasks/{task.id}")
        assert r.status_code == 409
        assert r.json()["msg"] == "进行中的任务不可删除，请先取消分析或等待处理完成"

    @pytest.mark.parametrize("status", ["failed", "completed", "dimension_review", "pending", "cancelled"])
    def test_deletable_returns_204(self, client, status):
        db = _db(client)
        task = _make_task(db, processing_status=status)
        assert client.delete(f"/api/v1/rfq/tasks/{task.id}").status_code == 204

    def test_deleted_task_not_found_on_get(self, client):
        db = _db(client)
        task = _make_task(db, processing_status="failed")
        client.delete(f"/api/v1/rfq/tasks/{task.id}")
        assert client.get(f"/api/v1/rfq/tasks/{task.id}").status_code == 404

    def test_deleted_absent_from_list(self, client):
        db = _db(client)
        task = _make_task(db, processing_status="failed", file_name="del_me.docx")
        client.delete(f"/api/v1/rfq/tasks/{task.id}")
        ids = {
            t["task_id"]
            for t in client.get("/api/v1/rfq/tasks", params={"unique_file": False}).json()["data"]
        }
        assert task.id not in ids

    def test_cleans_up_upload_file(self, client, tmp_path):
        rfq_file = tmp_path / "upload.docx"
        rfq_file.write_bytes(b"content")
        db = _db(client)
        task = _make_task(db, processing_status="failed", file_path=str(rfq_file))
        client.delete(f"/api/v1/rfq/tasks/{task.id}")
        assert not rfq_file.exists()

    def test_cleans_up_excel_output(self, client, tmp_path):
        excel_file = tmp_path / "out.xlsx"
        excel_file.write_bytes(b"xlsx")
        db = _db(client)
        task = RFQTask(
            file_name="t.docx",
            file_path=_ensure_stable_file(),
            processing_status="completed",
            excel_path=str(excel_file),
        )
        RFQTaskRepository(db).create(task)
        db.close()
        client.delete(f"/api/v1/rfq/tasks/{task.id}")
        assert not excel_file.exists()

    def test_missing_file_still_returns_204(self, client):
        db = _db(client)
        task = _make_task(db, processing_status="failed", file_path="/no/such/gone.docx")
        assert client.delete(f"/api/v1/rfq/tasks/{task.id}").status_code == 204

    def test_archived_task_can_be_deleted(self, client):
        db = _db(client)
        task = _make_task(db, processing_status="failed", archived=True)
        assert client.delete(f"/api/v1/rfq/tasks/{task.id}").status_code == 204


# =============================================================================
# Comprehensive archive endpoint tests
# =============================================================================

class TestArchiveComprehensive:

    def test_unknown_id_returns_404(self, client):
        assert client.patch("/api/v1/rfq/tasks/does-not-exist/archive").status_code == 404

    def test_unknown_id_message(self, client):
        assert client.patch("/api/v1/rfq/tasks/does-not-exist/archive").json()["msg"] == "任务 ID 不存在"

    @pytest.mark.parametrize("status", ["queued", "parsing", "retrieving", "generating", "cancelling"])
    def test_in_progress_returns_409(self, client, status):
        db = _db(client)
        task = _make_task(db, processing_status=status)
        r = client.patch(f"/api/v1/rfq/tasks/{task.id}/archive")
        assert r.status_code == 409
        assert r.json()["msg"] == "进行中的任务不可归档，请先取消分析或等待处理完成"

    @pytest.mark.parametrize("status", ["failed", "completed", "dimension_review", "pending", "cancelled"])
    def test_archivable_returns_200(self, client, status):
        db = _db(client)
        task = _make_task(db, processing_status=status)
        r = client.patch(f"/api/v1/rfq/tasks/{task.id}/archive")
        assert r.status_code == 200
        assert r.json()["code"] == 200

    def test_archived_hidden_from_default_list(self, client):
        db = _db(client)
        task = _make_task(db, processing_status="completed", file_name="arch.docx")
        client.patch(f"/api/v1/rfq/tasks/{task.id}/archive")
        ids = {
            t["task_id"]
            for t in client.get("/api/v1/rfq/tasks", params={"unique_file": False}).json()["data"]
        }
        assert task.id not in ids

    def test_archived_visible_with_include_archived_true(self, client):
        db = _db(client)
        task = _make_task(db, processing_status="completed", file_name="arch_vis.docx")
        client.patch(f"/api/v1/rfq/tasks/{task.id}/archive")
        ids = {
            t["task_id"]
            for t in client.get(
                "/api/v1/rfq/tasks", params={"unique_file": False, "include_archived": True}
            ).json()["data"]
        }
        assert task.id in ids

    def test_archive_twice_idempotent(self, client):
        db = _db(client)
        task = _make_task(db, processing_status="completed")
        assert client.patch(f"/api/v1/rfq/tasks/{task.id}/archive").status_code == 200
        assert client.patch(f"/api/v1/rfq/tasks/{task.id}/archive").status_code == 200

    def test_archive_blocks_retry(self, client):
        db = _db(client)
        task = _make_task(db, processing_status="failed")
        client.patch(f"/api/v1/rfq/tasks/{task.id}/archive")
        r = client.post(f"/api/v1/rfq/tasks/{task.id}/retry")
        assert r.status_code == 400
        assert r.json()["msg"] == "已归档任务不支持重试"


# =============================================================================
# Comprehensive upload queue limit tests
# =============================================================================

class TestQueueLimitComprehensive:

    def _set_limit(self, monkeypatch, limit):
        import app.api.v1.rfq as rfq_module
        from app.config import get_settings
        settings = get_settings()
        monkeypatch.setattr(settings, "task_max_queue_size", limit)
        monkeypatch.setattr(
            rfq_module.analysis_service.job_service, "uses_inline_worker", lambda: False
        )

    def test_zero_limit_returns_429(self, client, sample_rfq_bytes, monkeypatch):
        self._set_limit(monkeypatch, 0)
        r = _upload(client, sample_rfq_bytes)
        assert r.status_code == 429
        assert r.json()["code"] == 429
        assert "queue_depth" in r.json()
        assert r.json()["queue_depth"] == 0
        assert "队列" in r.json()["msg"]
        assert "稍后" in r.json()["msg"]

    def test_boundary_at_exact_limit_fails(self, client, sample_rfq_bytes, monkeypatch):
        import app.api.v1.rfq as rfq_module
        from app.config import get_settings
        monkeypatch.setattr(rfq_module.analysis_service.job_service, "uses_inline_worker", lambda: False)
        monkeypatch.setattr(get_settings(), "task_max_queue_size", 1)
        assert _upload(client, sample_rfq_bytes, "first.docx").status_code == 200
        assert _upload(client, sample_rfq_bytes, "second.docx").status_code == 429

    def test_large_limit_allows_upload(self, client, sample_rfq_bytes, monkeypatch):
        self._set_limit(monkeypatch, 100)
        r = _upload(client, sample_rfq_bytes)
        assert r.status_code == 200
        assert "task_id" in r.json()["data"]
        assert "file_id" in r.json()["data"]

    def test_invalid_extension_returns_400(self, client, monkeypatch):
        self._set_limit(monkeypatch, 100)
        r = client.post(
            "/api/v1/rfq/upload",
            files={"file": ("test.exe", b"binary", "application/octet-stream")},
        )
        assert r.status_code == 400


# =============================================================================
# List tasks - comprehensive parameter validation
# =============================================================================

class TestListTasksComprehensive:

    def test_default_excludes_archived(self, client):
        db = _db(client)
        t = _make_task(db, processing_status="completed", archived=True, file_name="hidden.docx")
        ids = {
            x["task_id"]
            for x in client.get("/api/v1/rfq/tasks", params={"unique_file": False}).json()["data"]
        }
        assert t.id not in ids

    def test_true_includes_archived(self, client):
        db = _db(client)
        t = _make_task(db, processing_status="completed", archived=True, file_name="vis.docx")
        ids = {
            x["task_id"]
            for x in client.get(
                "/api/v1/rfq/tasks", params={"unique_file": False, "include_archived": True}
            ).json()["data"]
        }
        assert t.id in ids

    def test_limit_parameter_respected(self, client):
        db = _db(client)
        for i in range(5):
            _make_task(db, processing_status="completed", file_name=f"lim{i}.docx")
        data = client.get(
            "/api/v1/rfq/tasks", params={"unique_file": False, "limit": 3}
        ).json()["data"]
        assert len(data) <= 3

    def test_response_structure(self, client):
        r = client.get("/api/v1/rfq/tasks")
        body = r.json()
        assert body["code"] == 200
        assert isinstance(body["data"], list)

    def test_task_row_required_fields(self, client):
        db = _db(client)
        _make_task(db, processing_status="completed")
        rows = client.get("/api/v1/rfq/tasks", params={"unique_file": False}).json()["data"]
        assert rows
        for field in ("task_id", "file_name", "status", "processing_status", "progress", "created_at"):
            assert field in rows[0], f"missing field: {field}"


# =============================================================================
# Integration: API call chains
# =============================================================================

class TestIntegrationChains:

    def test_fail_then_retry_flow(self, client, tmp_path, monkeypatch):
        import app.api.v1.rfq as rfq_module
        monkeypatch.setattr(rfq_module.analysis_service.job_service, "uses_inline_worker", lambda: False)
        rfq_file = tmp_path / "test.docx"
        rfq_file.write_bytes(b"content")
        db = _db(client)
        task = _make_task(db, processing_status="failed", error_msg="fail", file_path=str(rfq_file))
        retry = client.post(f"/api/v1/rfq/tasks/{task.id}/retry")
        assert retry.status_code == 200
        assert client.get(f"/api/v1/rfq/tasks/{task.id}/status").json()["status"] == "queued"

    def test_archive_then_delete(self, client):
        db = _db(client)
        task = _make_task(db, processing_status="completed")
        client.patch(f"/api/v1/rfq/tasks/{task.id}/archive")
        assert client.delete(f"/api/v1/rfq/tasks/{task.id}").status_code == 204
        assert client.get(f"/api/v1/rfq/tasks/{task.id}").status_code == 404

    def test_full_lifecycle(self, client):
        db = _db(client)
        task = _make_task(db, processing_status="completed", file_name="full.docx")
        assert task.id in {
            x["task_id"]
            for x in client.get("/api/v1/rfq/tasks", params={"unique_file": False}).json()["data"]
        }
        client.patch(f"/api/v1/rfq/tasks/{task.id}/archive")
        assert task.id not in {
            x["task_id"]
            for x in client.get("/api/v1/rfq/tasks", params={"unique_file": False}).json()["data"]
        }
        assert task.id in {
            x["task_id"]
            for x in client.get(
                "/api/v1/rfq/tasks", params={"unique_file": False, "include_archived": True}
            ).json()["data"]
        }
        assert client.delete(f"/api/v1/rfq/tasks/{task.id}").status_code == 204

    def test_retry_then_archive_blocked(self, client, tmp_path, monkeypatch):
        import app.api.v1.rfq as rfq_module
        monkeypatch.setattr(rfq_module.analysis_service.job_service, "uses_inline_worker", lambda: False)
        rfq_file = tmp_path / "test.docx"
        rfq_file.write_bytes(b"content")
        db = _db(client)
        task = _make_task(db, processing_status="failed", file_path=str(rfq_file))
        assert client.post(f"/api/v1/rfq/tasks/{task.id}/retry").status_code == 200
        assert client.patch(f"/api/v1/rfq/tasks/{task.id}/archive").status_code == 409

    def test_retry_then_delete_blocked(self, client, tmp_path, monkeypatch):
        import app.api.v1.rfq as rfq_module
        monkeypatch.setattr(rfq_module.analysis_service.job_service, "uses_inline_worker", lambda: False)
        rfq_file = tmp_path / "test.docx"
        rfq_file.write_bytes(b"content")
        db = _db(client)
        task = _make_task(db, processing_status="failed", file_path=str(rfq_file))
        assert client.post(f"/api/v1/rfq/tasks/{task.id}/retry").status_code == 200
        assert client.delete(f"/api/v1/rfq/tasks/{task.id}").status_code == 409

    def test_queue_full_delete_in_progress_blocked(self, client, sample_rfq_bytes, monkeypatch):
        import app.api.v1.rfq as rfq_module
        from app.config import get_settings
        monkeypatch.setattr(rfq_module.analysis_service.job_service, "uses_inline_worker", lambda: False)
        monkeypatch.setattr(get_settings(), "task_max_queue_size", 100)
        r = _upload(client, sample_rfq_bytes)
        assert r.status_code == 200
        task_id = r.json()["data"]["task_id"]
        assert client.delete(f"/api/v1/rfq/tasks/{task_id}").status_code == 409
