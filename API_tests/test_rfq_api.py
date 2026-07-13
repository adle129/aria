import time


def _wait_dimension_review(client, task_id: str) -> dict:
    for _ in range(30):
        status = client.get(f"/api/v1/rfq/tasks/{task_id}/status").json()
        if status["status"] == "dimension_review":
            return status
        if status["status"] in {"failed", "completed"}:
            break
        time.sleep(0.05)
    raise AssertionError(f"task {task_id} did not reach dimension_review")


def _confirm_dimensions(client, task_id: str) -> None:
    task = client.get(f"/api/v1/rfq/tasks/{task_id}").json()["data"]
    draft = task.get("dimension_draft") or {}
    items = draft.get("items") or []
    if not any(i.get("in_scope") for i in items):
        items = [{**items[0], "in_scope": True}] if items else []
    resp = client.post(
        f"/api/v1/rfq/tasks/{task_id}/confirm-dimensions",
        json={
            "baseline_version": draft.get("baseline_version"),
            "items": items,
            "custom_items": draft.get("custom_items") or [],
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["code"] == 200


def _wait_task_completed(client, task_id: str) -> None:
    for _ in range(30):
        status = client.get(f"/api/v1/rfq/tasks/{task_id}/status").json()
        if status["status"] in {"completed", "failed"}:
            return
        time.sleep(0.05)


def _upload_and_complete(client, sample_rfq_bytes, filename="mock_chassis_rfq.docx") -> str:
    upload = client.post(
        "/api/v1/rfq/upload",
        files={
            "file": (
                filename,
                sample_rfq_bytes,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )
    task_id = upload.json()["data"]["task_id"]
    _wait_dimension_review(client, task_id)
    _confirm_dimensions(client, task_id)
    _wait_task_completed(client, task_id)
    return task_id


def test_upload_docx_success(client, sample_rfq_bytes):
    response = client.post(
        "/api/v1/rfq/upload",
        files={"file": ("mock_chassis_rfq.docx", sample_rfq_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert "task_id" in body["data"]


def test_upload_non_word_rejected(client):
    response = client.post(
        "/api/v1/rfq/upload",
        files={"file": ("bad.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 400
    assert response.json()["code"] == 400
    assert "docx" in response.json()["msg"]
    assert ".doc" in response.json()["msg"]


def test_upload_doc_accepted(client, sample_rfq_bytes, monkeypatch):
    import app.api.v1.rfq as rfq_module

    monkeypatch.setattr(
        rfq_module.analysis_service.job_service,
        "uses_inline_worker",
        lambda: False,
    )
    response = client.post(
        "/api/v1/rfq/upload",
        files={
            "file": (
                "legacy_rfq.doc",
                sample_rfq_bytes,
                "application/msword",
            )
        },
    )
    assert response.status_code == 200
    assert response.json()["code"] == 200
    assert "task_id" in response.json()["data"]


def test_get_task_not_found(client):
    response = client.get("/api/v1/rfq/tasks/does-not-exist")
    assert response.status_code == 404


def test_list_tasks(client, sample_rfq_bytes):
    client.post(
        "/api/v1/rfq/upload",
        files={"file": ("mock_chassis_rfq.docx", sample_rfq_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    resp = client.get("/api/v1/rfq/tasks")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    assert len(body["data"]) >= 1
    row = body["data"][0]
    assert "progress" in row
    assert "status_message" in row
    assert "project_name" in row
    assert "customer" in row
    assert "file_name" in row


def test_list_tasks_keeps_same_filename_when_unique_file_false(client, sample_rfq_bytes):
    files = {
        "file": (
            "same_name.docx",
            sample_rfq_bytes,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    }
    first = client.post("/api/v1/rfq/upload", files=files).json()["data"]["task_id"]
    second = client.post("/api/v1/rfq/upload", files=files).json()["data"]["task_id"]
    assert first != second

    deduped = client.get("/api/v1/rfq/tasks", params={"unique_file": True}).json()["data"]
    same_name_deduped = [t for t in deduped if t["file_name"] == "same_name.docx"]
    assert len(same_name_deduped) == 1

    all_rows = client.get("/api/v1/rfq/tasks", params={"unique_file": False}).json()["data"]
    same_name_all = [t for t in all_rows if t["file_name"] == "same_name.docx"]
    assert {t["task_id"] for t in same_name_all} >= {first, second}


def test_upload_and_poll_until_completed(client, sample_rfq_bytes):
    task_id = _upload_and_complete(client, sample_rfq_bytes)
    task = client.get(f"/api/v1/rfq/tasks/{task_id}").json()["data"]
    assert task["processing_status"] == "completed"
    assert task["rfq_modules"]["platform_type"] == "MEB"
    assert task["comparison_table"]["overall_confidence"] in {"高", "中", "低"}
    assert "matrix_rows" in task["comparison_table"]
    assert "function_coverage" in task["comparison_table"]
    assert task["rfq_modules"].get("milestones")


def test_dimension_review_flow(client, sample_rfq_bytes):
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
    _wait_dimension_review(client, task_id)
    task = client.get(f"/api/v1/rfq/tasks/{task_id}").json()["data"]
    assert task["processing_status"] == "dimension_review"
    assert task["dimension_draft"] is not None
    assert len(task["dimension_draft"]["items"]) >= 1
    assert task["comparison_table"] is None
    assert task["artifacts_status"]["rfq_parsed"] is True
    assert task["artifacts_status"]["comparison_ready"] is False

    first = task["dimension_draft"]["items"][0]
    resp = client.put(
        f"/api/v1/rfq/tasks/{task_id}",
        json={
            "dimension_draft": {
                "items": [{**first, "in_scope": True, "work_content": "测试工作内容"}],
            }
        },
    )
    assert resp.status_code == 200
    updated = resp.json()["data"]
    assert updated["dimension_draft"]["items"][0]["work_content"] == "测试工作内容"

    all_off = [
        {"dimension_id": i["dimension_id"], "in_scope": False}
        for i in task["dimension_draft"]["items"]
    ]
    bad = client.post(f"/api/v1/rfq/tasks/{task_id}/confirm-dimensions", json={"items": all_off})
    assert bad.status_code == 400


def test_confirm_dimensions_then_matrix(client, sample_rfq_bytes):
    task_id = _upload_and_complete(client, sample_rfq_bytes)
    task = client.get(f"/api/v1/rfq/tasks/{task_id}").json()["data"]
    assert task["comparison_table"] is not None
    assert task["similar_projects"] is not None
    projects = task["comparison_table"].get("projects") or []
    assert projects
    dims = projects[0].get("dimensions") or {}
    assert dims, "comparison projects must expose per-dimension values"
    sample_dim = next(iter(dims.values()))
    assert "value" in sample_dim
    assert "match" in sample_dim


def test_update_task_comparison_and_confirm(client, sample_rfq_bytes):
    task_id = _upload_and_complete(client, sample_rfq_bytes)
    task = client.get(f"/api/v1/rfq/tasks/{task_id}").json()["data"]
    table = task["comparison_table"]
    table["matrix_rows"][0]["new_project"] = "MEB-修订"
    resp = client.put(
        f"/api/v1/rfq/tasks/{task_id}",
        json={"comparison_table": table, "confirmed": True},
    )
    assert resp.status_code == 200
    updated = resp.json()["data"]
    assert updated["status"] == "in_review"
    assert updated["comparison_table"]["matrix_rows"][0]["new_project"] == "MEB-修订"


def test_generate_excel_and_download(client, sample_rfq_bytes):
    task_id = _upload_and_complete(client, sample_rfq_bytes)

    blocked = client.post(f"/api/v1/rfq/tasks/{task_id}/generate-excel")
    assert blocked.status_code == 400

    client.put(f"/api/v1/rfq/tasks/{task_id}", json={"confirmed": True})
    gen = client.post(f"/api/v1/rfq/tasks/{task_id}/generate-excel")
    assert gen.status_code == 200
    data = gen.json()["data"]
    assert data["filename"].endswith(".xlsx")
    assert "manpower_plan" in data

    download = client.get(f"/api/v1/rfq/tasks/{task_id}/download/excel")
    assert download.status_code == 200
    assert "spreadsheetml" in download.headers.get("content-type", "")
    assert len(download.content) > 1000


def test_generate_proposal_stub(client, sample_rfq_bytes):
    task_id = _upload_and_complete(client, sample_rfq_bytes)

    blocked = client.post(f"/api/v1/rfq/tasks/{task_id}/generate-proposal")
    assert blocked.status_code == 200
    body = blocked.json()["data"]
    assert body["demo_preview"] is True
    assert len(body["solution_draft"]["sections"]) >= 1

    task = client.get(f"/api/v1/rfq/tasks/{task_id}").json()["data"]
    assert task["artifacts_status"]["proposal_ready"] is True
    assert task["solution_draft"] is not None


def test_generate_qa_stub(client, sample_rfq_bytes):
    task_id = _upload_and_complete(client, sample_rfq_bytes)

    resp = client.post(f"/api/v1/rfq/tasks/{task_id}/generate-qa")
    assert resp.status_code == 200
    body = resp.json()["data"]
    assert body["demo_preview"] is True
    assert len(body["qa_items"]) >= 3
    first = body["qa_items"][0]
    assert "question" in first and "function" in first and "impact" in first

    task = client.get(f"/api/v1/rfq/tasks/{task_id}").json()["data"]
    assert task["artifacts_status"]["qa_ready"] is True
    assert task["artifacts_status"]["qa_excel_ready"] is True
    assert body.get("filename", "").endswith(".xlsx")
    assert "download_url" in body

    download = client.get(f"/api/v1/rfq/tasks/{task_id}/download/qa")
    assert download.status_code == 200
    assert "spreadsheetml" in download.headers.get("content-type", "")
    assert len(download.content) > 1000


def test_download_qa_without_generate(client, sample_rfq_bytes):
    task_id = _upload_and_complete(client, sample_rfq_bytes)

    download = client.get(f"/api/v1/rfq/tasks/{task_id}/download/qa")
    assert download.status_code == 200
    assert "spreadsheetml" in download.headers.get("content-type", "")
    assert len(download.content) > 500


def test_artifacts_status_on_completed_task(client, sample_rfq_bytes):
    task_id = _upload_and_complete(client, sample_rfq_bytes)

    task = client.get(f"/api/v1/rfq/tasks/{task_id}").json()["data"]
    status = task["artifacts_status"]
    assert status["rfq_parsed"] is True
    assert status["comparison_ready"] is True
    assert status["proposal_ready"] is False
    assert status["qa_ready"] is False
    assert status["excel_ready"] is False


def test_manpower_breakdown_preview(client, sample_rfq_bytes):
    task_id = _upload_and_complete(client, sample_rfq_bytes)

    resp = client.get(f"/api/v1/rfq/tasks/{task_id}/manpower-breakdown-preview")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["demo_preview"] is True
    assert len(data["items"]) >= 1


def test_demo_multifunction_rfq_uncovered_functions(client, demo_multifunction_rfq_bytes):
    task_id = _upload_and_complete(client, demo_multifunction_rfq_bytes, "demo_multifunction_rfq.docx")

    task = client.get(f"/api/v1/rfq/tasks/{task_id}").json()["data"]
    coverage = task["comparison_table"]["function_coverage"]
    assert "BIW" in task["rfq_modules"]["functions_in_scope"]
    assert "EE" in task["rfq_modules"]["functions_in_scope"]
    assert "BIW" in coverage["uncovered"]
    assert "EE" in coverage["uncovered"]
