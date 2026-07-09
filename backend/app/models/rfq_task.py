import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, Column, DateTime, String, Text

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class RFQTask(Base):
    __tablename__ = "rfq_tasks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id = Column(String, nullable=True, index=True)
    file_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    module_type = Column(String, default="manpower")

    processing_status = Column(String, default="pending")
    review_status = Column(String, default="draft")

    progress = Column(String, default="0")
    status_message = Column(String, nullable=True)

    rfq_modules = Column(JSON, nullable=True)
    dimension_draft = Column(JSON, nullable=True)
    similar_projects = Column(JSON, nullable=True)
    comparison_table = Column(JSON, nullable=True)
    solution_draft = Column(JSON, nullable=True)
    qa_items = Column(JSON, nullable=True)
    excel_path = Column(String, nullable=True)
    qa_excel_path = Column(String, nullable=True)
    ppt_path = Column(String, nullable=True)
    error_msg = Column(Text, nullable=True)
    archived = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)
