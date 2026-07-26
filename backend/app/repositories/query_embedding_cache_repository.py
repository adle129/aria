from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.query_embedding_cache import QueryEmbeddingCache


class QueryEmbeddingCacheRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_key(self, cache_key: str) -> QueryEmbeddingCache | None:
        return self.db.scalar(
            select(QueryEmbeddingCache).where(QueryEmbeddingCache.cache_key == cache_key).limit(1)
        )

    def upsert(
        self,
        *,
        cache_key: str,
        query_hash: str,
        embedding_model: str,
        embedding: list[float],
    ) -> QueryEmbeddingCache:
        now = datetime.now(timezone.utc)
        row = self.get_by_key(cache_key)
        if row is None:
            row = QueryEmbeddingCache(
                cache_key=cache_key,
                query_hash=query_hash,
                embedding_model=embedding_model,
                embedding=embedding,
                hit_count=0,
                created_at=now,
            )
            self.db.add(row)
        else:
            row.query_hash = query_hash
            row.embedding_model = embedding_model
            row.embedding = embedding
            row.created_at = now
            row.last_hit_at = None
            row.hit_count = 0
        self.db.commit()
        self.db.refresh(row)
        return row

    def record_hit(self, row: QueryEmbeddingCache) -> QueryEmbeddingCache:
        row.hit_count = int(row.hit_count or 0) + 1
        row.last_hit_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(row)
        return row

    def delete(self, row: QueryEmbeddingCache) -> None:
        self.db.delete(row)
        self.db.commit()

    def purge_expired(self, *, ttl_seconds: int) -> int:
        if ttl_seconds <= 0:
            return 0
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=ttl_seconds)
        result = self.db.execute(
            delete(QueryEmbeddingCache).where(QueryEmbeddingCache.created_at < cutoff)
        )
        self.db.commit()
        return int(result.rowcount or 0)
