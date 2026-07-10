import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class KnowledgeImport(Base):
    __tablename__ = "knowledge_imports"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    job_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("task_jobs.id"),
        nullable=True,
        index=True,
    )
    triggered_by: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("users.id"),
        nullable=True,
    )
    batch_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    mode: Mapped[str] = mapped_column(String(32), nullable=False, default="incremental")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    generation_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("knowledge_index_generations.id"),
        nullable=True,
    )
    new_documents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    new_chunks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_files: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    engagements: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )
