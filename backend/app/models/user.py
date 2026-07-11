import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, String

from app.database import Base

USER_ROLE_QUOTE_ENGINEER = "quote_engineer"
USER_ROLE_KB_ADMIN = "kb_admin"
USER_ROLES = frozenset({USER_ROLE_QUOTE_ENGINEER, USER_ROLE_KB_ADMIN})


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    display_name = Column(String, nullable=False)
    role = Column(String, nullable=False, default=USER_ROLE_QUOTE_ENGINEER)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)
