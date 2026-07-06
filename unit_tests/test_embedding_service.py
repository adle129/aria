"""Unit tests for Ollama embedding truncation."""

from __future__ import annotations

from app.services.embedding_service import DEFAULT_EMBED_MAX_CHARS, truncate_for_embedding


def test_truncate_for_embedding_short_text_unchanged():
    text = "Area: BE\nQuestion: body material"
    assert truncate_for_embedding(text) == text


def test_truncate_for_embedding_long_text():
    text = "x" * 5000
    out = truncate_for_embedding(text, max_chars=2400)
    assert len(out) == 2400


def test_default_embed_max_chars_is_safe_for_nomic():
    assert DEFAULT_EMBED_MAX_CHARS <= 2500
