from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.knowledge_import import KnowledgeImport


class KnowledgeImportRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, import_id: str) -> KnowledgeImport | None:
        return self.db.get(KnowledgeImport, import_id)

    def get_by_job_id(self, job_id: str) -> KnowledgeImport | None:
        return self.db.scalar(
            select(KnowledgeImport).where(KnowledgeImport.job_id == job_id)
        )

    def create(self, record: KnowledgeImport) -> KnowledgeImport:
        now = datetime.now(timezone.utc)
        record.created_at = now
        record.updated_at = now
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def update(self, record: KnowledgeImport) -> KnowledgeImport:
        record.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(record)
        return record

    def list_recent(self, *, limit: int, offset: int) -> list[KnowledgeImport]:
        stmt = (
            select(KnowledgeImport)
            .order_by(KnowledgeImport.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.db.scalars(stmt).all())
