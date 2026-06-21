import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Project(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_name = Column(String, nullable=False)
    customer = Column(String, nullable=True)
    year = Column(Integer, nullable=True)
    doc_path = Column(String, nullable=False)
    ingested_at = Column(DateTime, default=_utcnow)
