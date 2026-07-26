import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class RfqParseCache(Base):
    """Content-addressed RFQ parse (+ auto dimension match) cache. No owner selections."""

    __tablename__ = "rfq_parse_cache"
    __table_args__ = (UniqueConstraint("cache_key", name="uq_rfq_parse_cache_key"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    cache_key: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    parser_version: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False)
    baseline_version: Mapped[str] = mapped_column(String(64), nullable=False)
    rfq_modules: Mapped[dict] = mapped_column(JSON, nullable=False)
    dimension_draft: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    hit_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )
    last_hit_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
