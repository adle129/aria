"""Unit tests for pgvector store availability and guards."""

from __future__ import annotations

import pytest

from app.services.pgvector_store import PgVectorStore, PgVectorUnavailableError


def test_is_available_false_on_sqlite():
    store = PgVectorStore(namespace="test")
    assert store.is_available() is False


def test_count_requires_postgresql():
    store = PgVectorStore(namespace="test")
    with pytest.raises(PgVectorUnavailableError, match="PostgreSQL"):
        store.count()


def test_list_source_docs_requires_postgresql():
    store = PgVectorStore(namespace="test")
    with pytest.raises(PgVectorUnavailableError, match="PostgreSQL"):
        store.list_source_docs()
