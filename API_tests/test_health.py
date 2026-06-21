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


def test_health_response_schema_keys(client):
    response = client.get("/api/v1/health")
    assert set(response.json().keys()) == {
        "status",
        "version",
        "model",
        "embedding_model",
        "mock_llm",
        "mock_rag",
        "ollama_reachable",
        "ollama_model_ready",
        "embedding_model_ready",
        "ollama_error",
    }
