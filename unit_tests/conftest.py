import os

import pytest

from app.config import get_settings

# Isolate unit tests from developer .env (e.g. OLLAMA_MODEL=qwen2.5:7b)
os.environ.setdefault("OLLAMA_MODEL", "qwen2.5:14b")
os.environ.setdefault("EMBEDDING_MODEL", "nomic-embed-text")
os.environ.setdefault("MOCK_LLM", "true")
os.environ.setdefault("MOCK_RAG", "true")


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
