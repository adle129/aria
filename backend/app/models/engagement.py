import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Engagement(Base):
    __tablename__ = "engagements"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    project_name: Mapped[str] = mapped_column(String(256), nullable=False)
    customer: Mapped[str | None] = mapped_column(String(256), nullable=True)
    year: Mapped[int | None] = mapped_column(nullable=True)
    functions: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    folder_path: Mapped[str] = mapped_column(String(512), nullable=False)
    manifest: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    index_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    last_indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
