from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.engagement import Engagement


class EngagementRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, engagement_id: str) -> Engagement | None:
        return self.db.get(Engagement, engagement_id)

    def list_all(
        self,
        *,
        customer: str | None = None,
        vehicle_model: str | None = None,
        space_id: str | None = None,
    ) -> list[Engagement]:
        stmt = select(Engagement).order_by(Engagement.id)
        if space_id and space_id.strip():
            stmt = stmt.where(Engagement.space_id == space_id.strip())
        if customer and customer.strip():
            stmt = stmt.where(Engagement.customer == customer.strip())
        if vehicle_model and vehicle_model.strip():
            stmt = stmt.where(Engagement.vehicle_model == vehicle_model.strip())
        return list(self.db.scalars(stmt).all())

    def upsert(self, engagement: Engagement) -> Engagement:
        existing = self.get_by_id(engagement.id)
        now = datetime.now(timezone.utc)
        if existing:
            existing.space_id = engagement.space_id or existing.space_id or "quoting"
            existing.project_name = engagement.project_name
            existing.customer = engagement.customer
            existing.vehicle_model = engagement.vehicle_model
            existing.year = engagement.year
            existing.functions = engagement.functions
            existing.folder_path = engagement.folder_path
            existing.manifest = engagement.manifest
            existing.index_status = engagement.index_status
            existing.tier = engagement.tier
            existing.content_hash = engagement.content_hash
            existing.uploaded_at = engagement.uploaded_at
            existing.uploaded_by = engagement.uploaded_by
            existing.last_indexed_at = engagement.last_indexed_at
            existing.last_error = engagement.last_error
            existing.updated_at = now
            self.db.commit()
            self.db.refresh(existing)
            return existing
        if not getattr(engagement, "space_id", None):
            engagement.space_id = "quoting"
        engagement.created_at = now
        engagement.updated_at = now
        self.db.add(engagement)
        self.db.commit()
        self.db.refresh(engagement)
        return engagement
