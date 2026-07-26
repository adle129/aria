"""PERF09: embed_texts respects query cache and skips it for KB index."""

from contextlib import contextmanager

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.database import Base
from app.models.knowledge_chunk import EMBEDDING_DIMENSION
from app.models.query_embedding_cache import QueryEmbeddingCache
from app.services import embedding_service
from app.services import query_embedding_cache_service as cache_mod
from app.services.embedding_service import embed_texts


def _vec() -> list[float]:
    return [0.01 * (i % 10) for i in range(EMBEDDING_DIMENSION)]


@pytest.fixture
def cache_db(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine, tables=[QueryEmbeddingCache.__table__])
    Session = sessionmaker(bind=engine)
    monkeypatch.setattr(cache_mod, "SessionLocal", Session)
    return Session


def _patch_embed_http(monkeypatch, fake_batch):
    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(embedding_service, "_try_batch_embed", fake_batch)
    monkeypatch.setattr(
        embedding_service,
        "ollama_http_client",
        lambda *_a, **_k: FakeClient(),
    )

    @contextmanager
    def _acquire(**_kwargs):
        yield

    class FakeGate:
        def acquire(self, **kwargs):
            return _acquire()

    monkeypatch.setattr(embedding_service, "get_ollama_gate", lambda _s: FakeGate())


def test_embed_texts_query_second_call_skips_ollama(cache_db, monkeypatch):
    settings = Settings(
        database_url="sqlite://",
        embedding_model="nomic-embed-text",
        query_embedding_cache_ttl_seconds=3600,
        ollama_global_scheduling_enabled=False,
    )
    calls = {"n": 0}

    def fake_batch(client, base, model, prompts):
        calls["n"] += 1
        return [_vec() for _ in prompts]

    _patch_embed_http(monkeypatch, fake_batch)

    v1 = embed_texts(settings, ["MEB Chassis"], request_type="rfq")
    v2 = embed_texts(settings, ["MEB Chassis"], request_type="rfq")
    assert v1 == v2
    assert len(v1[0]) == EMBEDDING_DIMENSION
    assert calls["n"] == 1
    session = cache_db()
    assert session.scalar(select(func.count()).select_from(QueryEmbeddingCache)) == 1
    session.close()


def test_embed_texts_kb_paths_do_not_cache(cache_db, monkeypatch):
    settings = Settings(
        database_url="sqlite://",
        embedding_model="nomic-embed-text",
        query_embedding_cache_ttl_seconds=3600,
        ollama_global_scheduling_enabled=False,
    )

    def fake_batch(client, base, model, prompts):
        return [_vec() for _ in prompts]

    _patch_embed_http(monkeypatch, fake_batch)

    embed_texts(settings, ["chunk body"], request_type="kb_full")
    embed_texts(settings, ["chunk body 2"], request_type="kb_incremental")
    session = cache_db()
    assert session.scalar(select(func.count()).select_from(QueryEmbeddingCache)) == 0
    session.close()


def test_embed_texts_continues_when_cache_lookup_errors(monkeypatch):
    settings = Settings(
        database_url="sqlite://",
        embedding_model="nomic-embed-text",
        query_embedding_cache_ttl_seconds=3600,
        ollama_global_scheduling_enabled=False,
    )

    def boom(*_a, **_k):
        raise RuntimeError("db down")

    monkeypatch.setattr(cache_mod.QueryEmbeddingCacheService, "lookup_vector", boom)
    monkeypatch.setattr(cache_mod.QueryEmbeddingCacheService, "store_vector", boom)

    def fake_batch(client, base, model, prompts):
        return [_vec() for _ in prompts]

    _patch_embed_http(monkeypatch, fake_batch)
    out = embed_texts(settings, ["still works"], request_type="query")
    assert len(out) == 1
    assert len(out[0]) == EMBEDDING_DIMENSION
