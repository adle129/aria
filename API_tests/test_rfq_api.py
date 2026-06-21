import time

from app.services.rag_service import RAGService
from app.config import Settings


def test_upload_docx_success(client, sample_rfq_bytes):
    response = client.post(
        "/api/v1/rfq/upload",
        files={"file": ("mock_chassis_rfq.docx", sample_rfq_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert "task_id" in body["data"]


def test_upload_non_docx_rejected(client):
    response = client.post(
        "/api/v1/rfq/upload",
        files={"file": ("bad.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 400
    assert response.json()["code"] == 400


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


def test_upload_and_poll_until_completed(client, sample_rfq_bytes):
    upload = client.post(
        "/api/v1/rfq/upload",
        files={"file": ("mock_chassis_rfq.docx", sample_rfq_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    task_id = upload.json()["data"]["task_id"]

    completed = False
    for _ in range(20):
        status = client.get(f"/api/v1/rfq/tasks/{task_id}/status").json()
        if status["status"] == "completed":
            completed = True
            break
        if status["status"] == "failed":
            break
        time.sleep(0.05)

    assert completed, "Background analysis should complete under mock mode"
    task = client.get(f"/api/v1/rfq/tasks/{task_id}").json()["data"]
    assert task["rfq_modules"]["platform_type"] == "MEB"
    assert task["comparison_table"]["overall_confidence"] in {"高", "中", "低"}
    assert "matrix_rows" in task["comparison_table"]
    assert task["rfq_modules"].get("milestones")


def test_update_task_comparison_and_confirm(client, sample_rfq_bytes):
    upload = client.post(
        "/api/v1/rfq/upload",
        files={"file": ("mock_chassis_rfq.docx", sample_rfq_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    task_id = upload.json()["data"]["task_id"]
    for _ in range(20):
        status = client.get(f"/api/v1/rfq/tasks/{task_id}/status").json()
        if status["status"] in {"completed", "failed"}:
            break
        time.sleep(0.05)

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


def _wait_task_completed(client, task_id: str) -> None:
    for _ in range(20):
        status = client.get(f"/api/v1/rfq/tasks/{task_id}/status").json()
        if status["status"] in {"completed", "failed"}:
            return
        time.sleep(0.05)


def test_generate_excel_and_download(client, sample_rfq_bytes):
    upload = client.post(
        "/api/v1/rfq/upload",
        files={"file": ("mock_chassis_rfq.docx", sample_rfq_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    task_id = upload.json()["data"]["task_id"]
    _wait_task_completed(client, task_id)

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
    upload = client.post(
        "/api/v1/rfq/upload",
        files={"file": ("mock_chassis_rfq.docx", sample_rfq_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    task_id = upload.json()["data"]["task_id"]
    _wait_task_completed(client, task_id)

    blocked = client.post(f"/api/v1/rfq/tasks/{task_id}/generate-proposal")
    assert blocked.status_code == 200
    body = blocked.json()["data"]
    assert body["demo_preview"] is True
    assert len(body["solution_draft"]["sections"]) >= 1

    task = client.get(f"/api/v1/rfq/tasks/{task_id}").json()["data"]
    assert task["artifacts_status"]["proposal_ready"] is True
    assert task["solution_draft"] is not None


def test_generate_qa_stub(client, sample_rfq_bytes):
    upload = client.post(
        "/api/v1/rfq/upload",
        files={"file": ("mock_chassis_rfq.docx", sample_rfq_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    task_id = upload.json()["data"]["task_id"]
    _wait_task_completed(client, task_id)

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
    upload = client.post(
        "/api/v1/rfq/upload",
        files={"file": ("mock_chassis_rfq.docx", sample_rfq_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    task_id = upload.json()["data"]["task_id"]
    _wait_task_completed(client, task_id)

    download = client.get(f"/api/v1/rfq/tasks/{task_id}/download/qa")
    assert download.status_code == 200
    assert "spreadsheetml" in download.headers.get("content-type", "")
    assert len(download.content) > 500


def test_artifacts_status_on_completed_task(client, sample_rfq_bytes):
    upload = client.post(
        "/api/v1/rfq/upload",
        files={"file": ("mock_chassis_rfq.docx", sample_rfq_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    task_id = upload.json()["data"]["task_id"]
    _wait_task_completed(client, task_id)

    task = client.get(f"/api/v1/rfq/tasks/{task_id}").json()["data"]
    status = task["artifacts_status"]
    assert status["rfq_parsed"] is True
    assert status["comparison_ready"] is True
    assert status["proposal_ready"] is False
    assert status["qa_ready"] is False
    assert status["excel_ready"] is False


def test_manpower_breakdown_preview(client, sample_rfq_bytes):
    upload = client.post(
        "/api/v1/rfq/upload",
        files={"file": ("mock_chassis_rfq.docx", sample_rfq_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    task_id = upload.json()["data"]["task_id"]
    _wait_task_completed(client, task_id)

    resp = client.get(f"/api/v1/rfq/tasks/{task_id}/manpower-breakdown-preview")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["demo_preview"] is True
    assert len(data["items"]) >= 1
