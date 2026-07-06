"""Unit tests for pgvector store (PostgreSQL required for integration)."""

from __future__ import annotations

import pytest

from app.services.pgvector_store import PgVectorStore


def test_is_available_false_on_sqlite():
    from app.config import Settings
    from app.database import engine

    if engine.dialect.name == "postgresql":
        pytest.skip("requires non-postgres dialect")
    store = PgVectorStore(namespace="test")
    assert store.is_available() is False


def test_require_pg_raises_on_sqlite():
    from app.database import engine

    if engine.dialect.name == "postgresql":
        pytest.skip("requires non-postgres dialect")
    store = PgVectorStore(namespace="test")
    with pytest.raises(Exception, match="pgvector"):
        store.count()
