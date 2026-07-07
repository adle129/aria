from app.config import get_settings


def test_knowledge_baselines_empty(client, upload_dir, monkeypatch):
    baselines_path = upload_dir / "baselines.json"
    monkeypatch.setenv("MANPOWER_BASELINES_PATH", str(baselines_path))
    get_settings.cache_clear()
    resp = client.get("/api/v1/knowledge/baselines")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "projects" in data
    assert data["projects"] == []


def test_knowledge_reindex_mock_mode(client):
    resp = client.post("/api/v1/knowledge/reindex")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "new_documents" in data
