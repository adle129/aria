from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class KnowledgeIndexGeneration(Base):
    __tablename__ = "knowledge_index_generations"

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    logical_namespace: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    created_by_job_id: Mapped[str | None] = mapped_column(String, nullable=True)
    schema_version: Mapped[str] = mapped_column(String(32), nullable=False, default="v1")
    embedding_model: Mapped[str] = mapped_column(String(128), nullable=False)
    content_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class KnowledgeIndexState(Base):
    __tablename__ = "knowledge_index_state"

    logical_namespace: Mapped[str] = mapped_column(String(64), primary_key=True)
    active_generation_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("knowledge_index_generations.id"),
        nullable=True,
    )
    previous_generation_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("knowledge_index_generations.id"),
        nullable=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
