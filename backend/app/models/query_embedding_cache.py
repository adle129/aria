import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class QueryEmbeddingCache(Base):
    """Short-TTL cache for query/rfq embedding vectors (PERF09). Not used for KB index."""

    __tablename__ = "query_embedding_cache"
    __table_args__ = (UniqueConstraint("cache_key", name="uq_query_embedding_cache_key"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    # sha256(64) + ":" + embedding_model(≤128) ≤ 193
    cache_key: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    query_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    embedding_model: Mapped[str] = mapped_column(String(128), nullable=False)
    embedding: Mapped[list] = mapped_column(JSON, nullable=False)
    hit_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    last_hit_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
