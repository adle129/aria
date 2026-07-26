"""API smoke: PERF09 cache table must not break health contracts."""

from sqlalchemy import select

from app.database import get_db
from app.main import app
from app.models.query_embedding_cache import QueryEmbeddingCache
from app.repositories.query_embedding_cache_repository import QueryEmbeddingCacheRepository


def _db(client):
    return next(app.dependency_overrides[get_db]())


def test_health_ok_with_embedding_cache_table(client):
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"


def test_seeded_embedding_cache_row_readable(client):
    db = _db(client)
    QueryEmbeddingCacheRepository(db).upsert(
        cache_key="abc:nomic-embed-text",
        query_hash="abc",
        embedding_model="nomic-embed-text",
        embedding=[0.1, 0.2],
    )
    db.close()

    db2 = _db(client)
    row = db2.scalar(
        select(QueryEmbeddingCache).where(QueryEmbeddingCache.query_hash == "abc").limit(1)
    )
    assert row is not None
    assert row.embedding == [0.1, 0.2]
    db2.close()
