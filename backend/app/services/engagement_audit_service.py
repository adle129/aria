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
from app.services.engagement_manifest_service import (
    ManifestLoadError,
    metadata_fields_complete,
    resolve_manifest,
    update_manifest_metadata,
)

class EngagementAuditError(ValueError):
    pass


class EngagementAuditNotFound(EngagementAuditError):
    pass


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
        existing = self.repo.get_by_id(manifest.engagement_id)
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
                # Keep prior index time until the next successful kb_index completes.
                last_indexed_at=existing.last_indexed_at if existing else None,
                last_error=existing.last_error if existing else None,
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

    def update_metadata(
        self,
        engagement_id: str,
        *,
        project_name: str | None = ...,
        customer: str | None = ...,
        year: int | None = ...,
        functions: list[str] | None = ...,
    ) -> dict[str, Any]:
        folder = self.kb_root / engagement_id
        if not folder.is_dir():
            raise EngagementAuditNotFound(f"项目不存在：{engagement_id}")
        try:
            manifest = update_manifest_metadata(
                folder,
                project_name=project_name,
                customer=customer,
                year=year,
                functions=functions,
            )
        except ManifestLoadError as exc:
            raise EngagementAuditError(str(exc)) from exc

        existing = self.repo.get_by_id(engagement_id)
        if existing is None:
            row = self.record_upload(folder, uploaded_by=None)
        else:
            row = self.repo.upsert(
                Engagement(
                    id=engagement_id,
                    project_name=manifest.project_name,
                    customer=manifest.customer,
                    year=manifest.year,
                    functions=list(manifest.functions or []),
                    folder_path=existing.folder_path,
                    manifest=manifest.model_dump(),
                    index_status=existing.index_status,
                    tier=existing.tier,
                    content_hash=existing.content_hash,
                    uploaded_at=existing.uploaded_at,
                    uploaded_by=existing.uploaded_by,
                    last_indexed_at=existing.last_indexed_at,
                    last_error=existing.last_error,
                )
            )
        return self.serialize_engagement(row, manifest=manifest)

    def serialize_engagement(
        self,
        row: Engagement,
        *,
        manifest: EngagementManifest | None = None,
    ) -> dict[str, Any]:
        if manifest is None:
            try:
                manifest = (
                    EngagementManifest.model_validate(row.manifest)
                    if row.manifest
                    else None
                )
            except Exception:
                manifest = None
            if manifest is None:
                folder = self.kb_root / row.id
                if folder.is_dir():
                    try:
                        manifest = resolve_manifest(folder)
                    except ManifestLoadError:
                        manifest = None
        complete = (
            metadata_fields_complete(manifest)
            if manifest is not None
            else bool(
                (row.project_name or "").strip()
                and (row.customer or "").strip()
                and row.year is not None
                and list(row.functions or [])
            )
        )
        return {
            "engagement_id": row.id,
            "project_name": row.project_name,
            "customer": row.customer,
            "year": row.year,
            "functions": list(row.functions or []),
            "tier": row.tier,
            "index_status": row.index_status,
            "content_hash": row.content_hash,
            "uploaded_at": row.uploaded_at,
            "uploaded_by": row.uploaded_by,
            "last_indexed_at": row.last_indexed_at,
            "last_error": row.last_error,
            "folder_path": row.folder_path,
            "metadata_complete": complete,
        }
