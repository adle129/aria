"""API tests for knowledge reindex (R1-K07)."""

from app.config import get_settings


def test_reindex_mock_mode(client):
    resp = client.post("/api/v1/knowledge/reindex")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "new_documents" in data
    assert "failed_files" in data


def test_reindex_production_returns_ingest_report(client, upload_dir, monkeypatch):
    monkeypatch.setenv("MOCK_RAG", "false")
    get_settings.cache_clear()

    expected = {
        "new_documents": 2,
        "new_chunks": 177,
        "skipped": 0,
        "failed_files": [],
        "last_import_at": "2026-07-07T00:00:00Z",
        "engagements_indexed": 1,
        "doc_type_counts": {"rfq": 142, "qa": 35},
    }

    class FakeIngest:
        def __init__(self, settings, db=None):
            pass

        def import_all(self):
            return expected

    monkeypatch.setattr(
        "app.api.v1.knowledge.EngagementIngestService",
        FakeIngest,
    )
    get_settings.cache_clear()
    resp = client.post("/api/v1/knowledge/reindex")
    assert resp.status_code == 200
    assert resp.json()["data"] == expected


def test_import_production_same_as_reindex(client, upload_dir, monkeypatch):
    monkeypatch.setenv("MOCK_RAG", "false")
    get_settings.cache_clear()

    calls = {"count": 0}

    class FakeIngest:
        def __init__(self, settings, db=None):
            pass

        def import_all(self):
            calls["count"] += 1
            return {
                "new_documents": 1,
                "new_chunks": 10,
                "skipped": 0,
                "failed_files": [],
                "last_import_at": "2026-07-07T00:00:00Z",
                "engagements_indexed": 1,
                "doc_type_counts": {"rfq": 5, "qa": 5},
            }

    monkeypatch.setattr(
        "app.api.v1.knowledge.EngagementIngestService",
        FakeIngest,
    )
    get_settings.cache_clear()
    import_resp = client.post("/api/v1/knowledge/import")
    reindex_resp = client.post("/api/v1/knowledge/reindex")
    assert import_resp.status_code == 200
    assert reindex_resp.status_code == 200
    assert calls["count"] == 2
