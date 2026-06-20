import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app


@pytest.fixture
def client(monkeypatch):
    """Isolate health API from local .env overrides."""
    monkeypatch.setenv("APP_VERSION", "1.0.0")
    monkeypatch.setenv("OLLAMA_MODEL", "qwen2.5:14b")
    monkeypatch.setenv("EMBEDDING_MODEL", "nomic-embed-text")
    monkeypatch.setenv("MOCK_LLM", "true")
    monkeypatch.setenv("MOCK_RAG", "true")
    get_settings.cache_clear()
    yield TestClient(app)
    get_settings.cache_clear()
