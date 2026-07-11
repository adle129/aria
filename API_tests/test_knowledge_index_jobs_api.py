from app.config import get_settings


def _production_jobs(monkeypatch) -> None:
    monkeypatch.setenv("MOCK_RAG", "false")
    get_settings.cache_clear()


def test_import_returns_202_and_reuses_active_job(client, monkeypatch):
    _production_jobs(monkeypatch)

    first = client.post("/api/v1/knowledge/import")
    second = client.post("/api/v1/knowledge/import")

    assert first.status_code == 202
    assert second.status_code == 202
    first_data = first.json()["data"]
    second_data = second.json()["data"]
    assert first_data["status"] == "queued"
    assert first_data["reused"] is False
    assert second_data["reused"] is True
    assert second_data["job_id"] == first_data["job_id"]


def test_active_detail_list_and_cancel_lifecycle(client, monkeypatch):
    _production_jobs(monkeypatch)
    created = client.post("/api/v1/knowledge/reindex").json()["data"]
    job_id = created["job_id"]

    active = client.get("/api/v1/knowledge/imports/active")
    detail = client.get(f"/api/v1/knowledge/imports/{job_id}")
    listing = client.get("/api/v1/knowledge/imports")
    cancelled = client.post(f"/api/v1/knowledge/imports/{job_id}/cancel")
    no_active = client.get("/api/v1/knowledge/imports/active")

    assert active.status_code == 200
    assert active.json()["data"]["job_id"] == job_id
    assert detail.json()["data"]["mode"] == "full"
    assert listing.json()["data"]["jobs"][0]["job_id"] == job_id
    assert cancelled.json()["data"]["status"] == "cancelled"
    assert no_active.json()["data"] is None


def test_unknown_import_job_returns_404(client):
    response = client.get("/api/v1/knowledge/imports/not-found")

    assert response.status_code == 404
    assert response.json()["msg"] == "索引任务不存在"
