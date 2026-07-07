from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.engagement import Engagement


class EngagementRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, engagement_id: str) -> Engagement | None:
        return self.db.get(Engagement, engagement_id)

    def list_all(self) -> list[Engagement]:
        return list(self.db.scalars(select(Engagement).order_by(Engagement.id)).all())

    def upsert(self, engagement: Engagement) -> Engagement:
        existing = self.get_by_id(engagement.id)
        now = datetime.now(timezone.utc)
        if existing:
            existing.project_name = engagement.project_name
            existing.customer = engagement.customer
            existing.year = engagement.year
            existing.functions = engagement.functions
            existing.folder_path = engagement.folder_path
            existing.manifest = engagement.manifest
            existing.index_status = engagement.index_status
            existing.last_indexed_at = engagement.last_indexed_at
            existing.last_error = engagement.last_error
            existing.updated_at = now
            self.db.commit()
            self.db.refresh(existing)
            return existing
        engagement.created_at = now
        engagement.updated_at = now
        self.db.add(engagement)
        self.db.commit()
        self.db.refresh(engagement)
        return engagement
