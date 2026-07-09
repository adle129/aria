"""Unit tests for Ollama embedding truncation."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.config import Settings
from app.services.embedding_service import (
    DEFAULT_EMBED_MAX_CHARS,
    EmbeddingError,
    embed_texts,
    truncate_for_embedding,
)


def test_truncate_for_embedding_short_text_unchanged():
    text = "Area: BE\nQuestion: body material"
    assert truncate_for_embedding(text) == text


def test_truncate_for_embedding_long_text():
    text = "x" * 5000
    out = truncate_for_embedding(text, max_chars=2400)
    assert len(out) == 2400


def test_default_embed_max_chars_is_safe_for_nomic():
    assert DEFAULT_EMBED_MAX_CHARS <= 2500


def test_embed_texts_batch_endpoint(monkeypatch):
    """embed_texts prefers the batch /api/embed endpoint (Ollama >=0.3)."""
    settings = Settings(
        ollama_base_url="http://ollama.test",
        embedding_model="nomic-embed-text",
        embedding_max_chars=2400,
    )
    calls: list[dict] = []

    class FakeResponse:
        def __init__(self, data):
            self._data = data
            self.status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return self._data

    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url, json=None, **kwargs):
            calls.append({"url": url, "json": json})
            if url.endswith("/api/embed"):
                embeddings = [[0.1, 0.2, 0.3] for _ in json.get("input", [])]
                return FakeResponse({"embeddings": embeddings})
            return FakeResponse({"embedding": [0.1, 0.2, 0.3]})

    monkeypatch.setattr(
        "app.services.embedding_service.ollama_http_client",
        lambda _timeout: FakeClient(),
    )

    vectors = embed_texts(settings, ["hello", "world"])
    assert len(vectors) == 2
    assert len(vectors[0]) == 3
    # Should use batch endpoint first
    assert calls[0]["url"] == "http://ollama.test/api/embed"
    assert calls[0]["json"]["model"] == "nomic-embed-text"
    assert calls[0]["json"]["input"] == ["hello", "world"]


def test_embed_texts_falls_back_to_serial(monkeypatch):
    """Falls back to serial /api/embeddings when /api/embed returns 404."""
    settings = Settings(
        ollama_base_url="http://ollama.test",
        embedding_model="nomic-embed-text",
        embedding_max_chars=2400,
    )
    calls: list[dict] = []

    class FakeResponse404:
        status_code = 404

        def raise_for_status(self):
            return None

        def json(self):
            return {}

    class FakeResponseOk:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {"embedding": [0.1, 0.2, 0.3]}

    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url, json=None, **kwargs):
            calls.append(url)
            if url.endswith("/api/embed"):
                return FakeResponse404()
            return FakeResponseOk()

    monkeypatch.setattr(
        "app.services.embedding_service.ollama_http_client",
        lambda _timeout: FakeClient(),
    )

    vectors = embed_texts(settings, ["hello", "world"])
    assert len(vectors) == 2
    assert calls[0].endswith("/api/embed")       # tried batch first
    assert calls[1].endswith("/api/embeddings")  # fell back to serial


def test_embed_texts_empty_input():
    assert embed_texts(Settings(), []) == []


def test_embed_texts_http_error_raises(monkeypatch):
    import httpx

    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url, json=None, **kwargs):
            raise httpx.ConnectError("down", request=MagicMock())

    monkeypatch.setattr(
        "app.services.embedding_service.ollama_http_client",
        lambda _timeout: FakeClient(),
    )
    with pytest.raises(EmbeddingError, match="Ollama embedding failed"):
        embed_texts(Settings(), ["hello"])
