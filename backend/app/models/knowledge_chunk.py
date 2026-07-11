"""Knowledge chunk vectors (R1 · PostgreSQL pgvector)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

try:
    from pgvector.sqlalchemy import Vector
except ImportError:  # pragma: no cover - optional at import time in minimal env
    Vector = None  # type: ignore[misc, assignment]


EMBEDDING_DIMENSION = 768  # nomic-embed-text


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    generation_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    chunk_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    namespace: Mapped[str] = mapped_column(String(64), nullable=False, index=True, default="default")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    if Vector is not None:
        embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIMENSION), nullable=True)
    chunk_metadata: Mapped[dict] = mapped_column(
        "metadata",
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
