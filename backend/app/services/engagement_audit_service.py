from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.config import Settings
from app.models.engagement import Engagement
from app.repositories.engagement_repository import EngagementRepository
from app.schemas.engagement import EngagementManifest
from app.services.engagement_completeness import classify_engagement
from app.services.engagement_content_hash import compute_engagement_content_hash
from app.services.engagement_manifest_service import resolve_manifest
from app.services.ingest.engagement_preview import build_engagement_preview


class EngagementAuditService:
    def __init__(self, settings: Settings, db: Session):
        self.settings = settings
        self.db = db
        self.kb_root = Path(settings.knowledge_base_path)
        self.repo = EngagementRepository(db)

    def record_upload(
        self,
        folder: Path,
        *,
        uploaded_by: str | None,
        tier: str | None = None,
        missing: list[str] | None = None,
    ) -> Engagement:
        folder = Path(folder)
        manifest = resolve_manifest(folder)
        completeness = classify_engagement(missing or [])
        rel = str(folder.relative_to(self.kb_root)).replace("\\", "/")
        now = datetime.now(UTC)
        return self.repo.upsert(
            Engagement(
                id=manifest.engagement_id,
                project_name=manifest.project_name,
                customer=manifest.customer,
                year=manifest.year,
                functions=list(manifest.functions or []),
                folder_path=rel,
                manifest=manifest.model_dump(),
                index_status="pending",
                tier=tier or completeness["tier"],
                content_hash=compute_engagement_content_hash(folder),
                uploaded_at=now,
                uploaded_by=uploaded_by,
            )
        )

    def record_upload_pack(
        self,
        pack: dict[str, Any],
        *,
        uploaded_by: str | None,
    ) -> Engagement | None:
        engagement_id = pack.get("engagement_id")
        if not engagement_id:
            return None
        folder = self.kb_root / engagement_id
        if not folder.is_dir():
            return None
        return self.record_upload(
            folder,
            uploaded_by=uploaded_by,
            tier=pack.get("tier"),
            missing=pack.get("missing"),
        )

    def refresh_content_hash(self, engagement_id: str) -> str | None:
        folder = self.kb_root / engagement_id
        if not folder.is_dir():
            return None
        content_hash = compute_engagement_content_hash(folder)
        existing = self.repo.get_by_id(engagement_id)
        if existing is None:
            return content_hash
        existing.content_hash = content_hash
        self.repo.upsert(existing)
        return content_hash
