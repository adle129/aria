"""R1-PERF09: short-TTL query embedding cache (PG; no Redis)."""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import SessionLocal
from app.models.knowledge_chunk import EMBEDDING_DIMENSION
from app.repositories.query_embedding_cache_repository import QueryEmbeddingCacheRepository

logger = logging.getLogger(__name__)

# Only interactive search / RFQ confirm paths — never KB index batches.
CACHEABLE_REQUEST_TYPES = frozenset({"query", "rfq"})


def normalize_query_for_cache(text: str) -> str:
    return " ".join((text or "").split())


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_cache_key(*, query_hash: str, embedding_model: str) -> str:
    return f"{query_hash}:{embedding_model}"


def embedding_usable(embedding: Any) -> bool:
    if not isinstance(embedding, list) or len(embedding) != EMBEDDING_DIMENSION:
        return False
    return all(isinstance(x, (int, float)) for x in embedding)


class QueryEmbeddingCacheService:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    @property
    def enabled(self) -> bool:
        return int(self.settings.query_embedding_cache_ttl_seconds or 0) > 0

    def is_cacheable_request(self, request_type: str) -> bool:
        return request_type in CACHEABLE_REQUEST_TYPES

    def lookup_vector(self, prompt: str) -> list[float] | None:
        if not self.enabled:
            return None
        db = SessionLocal()
        try:
            return self._lookup(db, prompt)
        except Exception:
            logger.exception("query_embedding_cache_lookup_failed")
            return None
        finally:
            db.close()

    def store_vector(self, prompt: str, embedding: list[float]) -> None:
        if not self.enabled or not embedding_usable(embedding):
            return
        db = SessionLocal()
        try:
            self._store(db, prompt, embedding)
        except Exception:
            logger.exception("query_embedding_cache_store_failed")
        finally:
            db.close()

    def _lookup(self, db: Session, prompt: str) -> list[float] | None:
        normalized = normalize_query_for_cache(prompt)
        if not normalized:
            return None
        query_hash = sha256_text(normalized)
        cache_key = build_cache_key(
            query_hash=query_hash,
            embedding_model=self.settings.embedding_model,
        )
        repo = QueryEmbeddingCacheRepository(db)
        row = repo.get_by_key(cache_key)
        if row is None:
            return None
        ttl = int(self.settings.query_embedding_cache_ttl_seconds)
        created = row.created_at
        if created is not None and created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        if created is None or datetime.now(timezone.utc) - created > timedelta(seconds=ttl):
            try:
                repo.delete(row)
            except Exception:
                logger.exception("query_embedding_cache_expire_delete_failed")
            return None
        if not embedding_usable(row.embedding):
            try:
                repo.delete(row)
            except Exception:
                logger.exception("query_embedding_cache_corrupt_delete_failed")
            return None
        try:
            repo.record_hit(row)
        except Exception:
            logger.exception("query_embedding_cache_hit_count_failed")
        logger.info(
            "query_embedding_cache_hit key=%s hits=%s model=%s",
            cache_key[:24],
            row.hit_count,
            self.settings.embedding_model,
        )
        return [float(x) for x in row.embedding]

    def _store(self, db: Session, prompt: str, embedding: list[float]) -> None:
        normalized = normalize_query_for_cache(prompt)
        if not normalized:
            return
        query_hash = sha256_text(normalized)
        cache_key = build_cache_key(
            query_hash=query_hash,
            embedding_model=self.settings.embedding_model,
        )
        repo = QueryEmbeddingCacheRepository(db)
        try:
            repo.purge_expired(ttl_seconds=int(self.settings.query_embedding_cache_ttl_seconds))
        except Exception:
            logger.exception("query_embedding_cache_purge_failed")
            try:
                db.rollback()
            except Exception:
                logger.exception("query_embedding_cache_purge_rollback_failed")
        repo.upsert(
            cache_key=cache_key,
            query_hash=query_hash,
            embedding_model=self.settings.embedding_model,
            embedding=[float(x) for x in embedding],
        )
        logger.info("query_embedding_cache_store key=%s", cache_key[:24])
