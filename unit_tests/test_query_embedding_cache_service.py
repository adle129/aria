from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.database import Base
from app.models.knowledge_chunk import EMBEDDING_DIMENSION
from app.models.query_embedding_cache import QueryEmbeddingCache
from app.services import query_embedding_cache_service as cache_mod
from app.services.query_embedding_cache_service import (
    CACHEABLE_REQUEST_TYPES,
    QueryEmbeddingCacheService,
    build_cache_key,
    embedding_usable,
    normalize_query_for_cache,
    sha256_text,
)


def _vec(seed: float = 0.1) -> list[float]:
    return [seed + i * 0.0001 for i in range(EMBEDDING_DIMENSION)]


@pytest.fixture
def db_session(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine, tables=[QueryEmbeddingCache.__table__])
    Session = sessionmaker(bind=engine)
    monkeypatch.setattr(cache_mod, "SessionLocal", Session)
    session = Session()
    yield session
    session.close()


def test_normalize_and_key_stable():
    assert normalize_query_for_cache("  MEB   Chassis \n") == "MEB Chassis"
    h = sha256_text("MEB Chassis")
    key = build_cache_key(query_hash=h, embedding_model="nomic-embed-text")
    assert key.startswith(h)
    assert key.endswith("nomic-embed-text")
    assert len(key) <= 256


def test_cacheable_request_types():
    assert "query" in CACHEABLE_REQUEST_TYPES
    assert "rfq" in CACHEABLE_REQUEST_TYPES
    assert "kb_full" not in CACHEABLE_REQUEST_TYPES
    assert "kb_incremental" not in CACHEABLE_REQUEST_TYPES


def test_embedding_usable_requires_dimension():
    assert embedding_usable(_vec()) is True
    assert embedding_usable([0.1, 0.2, 0.3]) is False
    assert embedding_usable([]) is False
    assert embedding_usable("bad") is False


def test_store_and_lookup_roundtrip(db_session):
    svc = QueryEmbeddingCacheService(
        Settings(
            database_url="sqlite://",
            embedding_model="nomic-embed-text",
            query_embedding_cache_ttl_seconds=3600,
        )
    )
    vec = _vec(0.1)
    assert svc.lookup_vector("MEB Chassis") is None
    svc.store_vector("MEB Chassis", vec)
    hit = svc.lookup_vector("  MEB   Chassis ")
    assert hit == vec
    assert db_session.scalar(select(func.count()).select_from(QueryEmbeddingCache)) == 1


def test_rejects_wrong_dimension_on_store(db_session):
    svc = QueryEmbeddingCacheService(
        Settings(
            database_url="sqlite://",
            embedding_model="nomic-embed-text",
            query_embedding_cache_ttl_seconds=3600,
        )
    )
    svc.store_vector("short", [0.1, 0.2, 0.3])
    assert db_session.scalar(select(func.count()).select_from(QueryEmbeddingCache)) == 0


def test_corrupt_row_dropped_on_lookup(db_session):
    svc = QueryEmbeddingCacheService(
        Settings(
            database_url="sqlite://",
            embedding_model="nomic-embed-text",
            query_embedding_cache_ttl_seconds=3600,
        )
    )
    svc.store_vector("ok", _vec(0.2))
    row = db_session.scalar(select(QueryEmbeddingCache).limit(1))
    assert row is not None
    row.embedding = [0.1, 0.2]
    db_session.commit()
    assert svc.lookup_vector("ok") is None
    assert db_session.scalar(select(func.count()).select_from(QueryEmbeddingCache)) == 0


def test_model_name_change_misses(db_session):
    svc_a = QueryEmbeddingCacheService(
        Settings(
            database_url="sqlite://",
            embedding_model="nomic-embed-text",
            query_embedding_cache_ttl_seconds=3600,
        )
    )
    svc_a.store_vector("same query", _vec(1.0))
    svc_b = QueryEmbeddingCacheService(
        Settings(
            database_url="sqlite://",
            embedding_model="other-embed",
            query_embedding_cache_ttl_seconds=3600,
        )
    )
    assert svc_b.lookup_vector("same query") is None


def test_ttl_expiry_misses(db_session):
    svc = QueryEmbeddingCacheService(
        Settings(
            database_url="sqlite://",
            embedding_model="nomic-embed-text",
            query_embedding_cache_ttl_seconds=60,
        )
    )
    svc.store_vector("old", _vec(0.5))
    row = db_session.scalar(select(QueryEmbeddingCache).limit(1))
    assert row is not None
    row.created_at = datetime.now(timezone.utc) - timedelta(hours=2)
    db_session.commit()
    assert svc.lookup_vector("old") is None


def test_disabled_when_ttl_zero(db_session):
    svc = QueryEmbeddingCacheService(
        Settings(
            database_url="sqlite://",
            embedding_model="nomic-embed-text",
            query_embedding_cache_ttl_seconds=0,
        )
    )
    assert svc.enabled is False
    svc.store_vector("x", _vec())
    assert svc.lookup_vector("x") is None
