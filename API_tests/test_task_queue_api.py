import time

from app.models.task_job import TaskJob


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


def test_knowledge_search_includes_insufficient_evidence(client):
    response = client.post("/api/v1/knowledge/search", json={"query": "MEB chassis", "top_k": 3})
    assert response.status_code == 200
    data = response.json()["data"]
    assert "insufficient_evidence" in data
    assert data["insufficient_evidence"] is False
