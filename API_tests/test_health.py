def test_health_returns_ok(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"] == "1.0.0"
    assert body["model"] == "qwen2.5:14b"
    assert body["embedding_model"] == "nomic-embed-text"
    assert body["mock_llm"] is True
    assert body["mock_rag"] is True
    assert "ollama_reachable" in body
    assert body["data_volume"]["total_bytes"] >= body["data_volume"]["free_bytes"]
    assert "write_protected" in body["temp_volume"]


def test_health_response_schema_keys(client):
    response = client.get("/api/v1/health")
    assert set(response.json().keys()) == {
        "status",
        "version",
        "deploy_sha",
        "packaged_at",
        "model",
        "embedding_model",
        "mock_llm",
        "mock_rag",
        "ollama_reachable",
        "ollama_model_ready",
        "embedding_model_ready",
        "ollama_error",
        "kb_debug_enabled",
        "aria_ui_profile",
        "auth_enabled",
        "production_warnings",
        "data_volume",
        "temp_volume",
    }


def test_health_includes_deploy_sha(client, monkeypatch):
    from app.config import get_settings

    monkeypatch.setenv("DEPLOY_SHA", "abc1234-test")
    monkeypatch.setenv("PACKAGED_AT", "2026-07-11T12:00:00Z")
    get_settings.cache_clear()
    try:
        body = client.get("/api/v1/health").json()
        assert body["deploy_sha"] == "abc1234-test"
        assert body["packaged_at"] == "2026-07-11T12:00:00Z"
    finally:
        get_settings.cache_clear()
