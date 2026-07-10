import json

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


def test_knowledge_baselines_filter_by_engagement(client, upload_dir, monkeypatch):
    baselines_path = upload_dir / "baselines.json"
    monkeypatch.setenv("MANPOWER_BASELINES_PATH", str(baselines_path))
    get_settings.cache_clear()
    baselines_path.write_text(
        json.dumps(
            {
                "version": 1,
                "projects": [
                    {
                        "engagement_id": "eng_a",
                        "project_name": "Alpha",
                        "functions": {"PM": {"total_man_days": 12, "positions": []}},
                    },
                    {
                        "engagement_id": "eng_b",
                        "project_name": "Beta",
                        "functions": {"Chassis": {"total_man_days": 8, "positions": []}},
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    get_settings.cache_clear()

    resp = client.get("/api/v1/knowledge/baselines", params={"engagement_id": "eng_a"})
    assert resp.status_code == 200
    projects = resp.json()["data"]["projects"]
    assert len(projects) == 1
    assert projects[0]["engagement_id"] == "eng_a"

    resp_fn = client.get("/api/v1/knowledge/baselines", params={"function": "Chassis"})
    assert resp_fn.status_code == 200
    assert len(resp_fn.json()["data"]["projects"]) == 1
    assert "Chassis" in resp_fn.json()["data"]["projects"][0]["functions"]


def test_knowledge_reindex_mock_mode(client):
    resp = client.post("/api/v1/knowledge/reindex")
    assert resp.status_code == 202
    data = resp.json()["data"]
    assert data["job_id"]
    assert data["status"] == "completed"
