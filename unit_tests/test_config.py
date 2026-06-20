import pytest

from app.config import Settings, get_settings


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_settings_defaults(monkeypatch):
    monkeypatch.setenv("MOCK_LLM", "true")
    monkeypatch.setenv("MOCK_RAG", "true")
    settings = Settings()
    assert settings.app_version == "1.0.0"
    assert settings.ollama_model == "qwen2.5:14b"
    assert settings.embedding_model == "nomic-embed-text"
    assert settings.mock_llm is True
    assert settings.mock_rag is True


def test_get_settings_cached():
    assert get_settings() is get_settings()
