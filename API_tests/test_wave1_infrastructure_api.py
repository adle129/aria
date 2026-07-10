"""API tests for R1 Wave 1 infrastructure (queue + empty-index rejection)."""

from app.config import get_settings


def test_upload_remains_queued_without_inline_worker(client, sample_rfq_bytes, monkeypatch):
    import app.api.v1.rfq as rfq_module

    monkeypatch.setattr(
        rfq_module.analysis_service.job_service,
        "uses_inline_worker",
        lambda: False,
    )

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
    assert upload.status_code == 200
    task_id = upload.json()["data"]["task_id"]
    status = client.get(f"/api/v1/rfq/tasks/{task_id}/status").json()
    assert status["status"] == "queued"
    assert status["queue_position"] == 1
    assert status["estimated_wait_seconds"] >= 0


def test_knowledge_search_insufficient_evidence_empty_index(client, monkeypatch):
    monkeypatch.setenv("MOCK_RAG", "false")
    get_settings.cache_clear()

    class FakeIndex:
        def search(self, query=None, **_kwargs):
            return []

    monkeypatch.setattr(
        "app.services.knowledge_index_service.KnowledgeIndexService",
        lambda _settings, namespace=None: FakeIndex(),
    )

    response = client.post(
        "/api/v1/knowledge/search",
        json={"query": "MEB chassis suspension scope", "top_k": 3},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["results"] == []
    assert data["insufficient_evidence"] is True


def test_knowledge_reindex_queues_job_in_production_mode(client, monkeypatch):
    monkeypatch.setenv("MOCK_RAG", "false")
    get_settings.cache_clear()

    response = client.post("/api/v1/knowledge/reindex")
    assert response.status_code == 202
    data = response.json()["data"]
    assert data["status"] == "queued"
    assert data["job_id"]
    assert data["reused"] is False
