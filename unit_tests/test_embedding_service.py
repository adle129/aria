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


def test_embed_texts_calls_ollama(monkeypatch):
    settings = Settings(
        ollama_base_url="http://ollama.test",
        embedding_model="nomic-embed-text",
        embedding_max_chars=2400,
    )
    calls: list[dict] = []

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"embedding": [0.1, 0.2, 0.3]}

    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url, json):
            calls.append({"url": url, "json": json})
            return FakeResponse()

    monkeypatch.setattr(
        "app.services.embedding_service.ollama_http_client",
        lambda _timeout: FakeClient(),
    )

    vectors = embed_texts(settings, ["hello", "world"])
    assert len(vectors) == 2
    assert len(vectors[0]) == 3
    assert calls[0]["url"] == "http://ollama.test/api/embeddings"
    assert calls[0]["json"]["model"] == "nomic-embed-text"
    assert calls[0]["json"]["prompt"] == "hello"


def test_embed_texts_empty_input():
    assert embed_texts(Settings(), []) == []


def test_embed_texts_http_error_raises(monkeypatch):
    import httpx

    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url, json):
            raise httpx.ConnectError("down", request=MagicMock())

    monkeypatch.setattr(
        "app.services.embedding_service.ollama_http_client",
        lambda _timeout: FakeClient(),
    )
    with pytest.raises(EmbeddingError, match="Ollama embedding failed"):
        embed_texts(Settings(), ["hello"])
