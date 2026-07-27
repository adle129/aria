"""Move engagements to / restore from trash (R1-CHG14 L2)."""

from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.config import Settings
from app.repositories.engagement_repository import EngagementRepository
from app.services.engagement_audit_service import EngagementAuditService
from app.services.engagement_manifest_service import resolve_manifest
from app.services.engagement_reference_service import (
    EngagementReferenceService,
    can_soft_delete_engagement,
)
from app.services.knowledge_space import require_known_space
from app.services.manpower_baselines_store import ManpowerBaselinesStore

TRASH_RETENTION_DAYS = 30
TRASH_META_NAME = "trash_meta.json"


class EngagementTrashError(ValueError):
    pass


class EngagementTrashNotFound(EngagementTrashError):
    pass


class EngagementTrashConflict(EngagementTrashError):
    def __init__(self, message: str, *, ref_task_ids: list[str] | None = None):
        super().__init__(message)
        self.ref_task_ids = list(ref_task_ids or [])


def trash_root_for(settings: Settings) -> Path:
    kb = Path(settings.knowledge_base_path)
    return kb.parent / "trash"


class EngagementTrashService:
    def __init__(self, settings: Settings, db: Session):
        self.settings = settings
        self.db = db
        self.kb_root = Path(settings.knowledge_base_path)
        self.trash_root = trash_root_for(settings)
        self.repo = EngagementRepository(db)
        self.refs = EngagementReferenceService(db)

    def soft_delete(
        self,
        engagement_id: str,
        *,
        deleted_by: str | None = None,
        force_policy: bool = False,
    ) -> dict[str, Any]:
        engagement_id = (engagement_id or "").strip()
        folder = self.kb_root / engagement_id
        if not folder.is_dir():
            raise EngagementTrashNotFound(f"项目不存在：{engagement_id}")

        ref_ids = self.refs.list_hard_ref_task_ids(engagement_id)
        if ref_ids:
            raise EngagementTrashConflict(
                "有报价任务在使用本项目，无法删除",
                ref_task_ids=ref_ids,
            )

        row = self.repo.get_by_id(engagement_id)
        tier = row.tier if row else None
        index_status = row.index_status if row else None

        try:
            manifest = resolve_manifest(folder)
            space_id = require_known_space(
                getattr(manifest, "space_id", None)
                or (row.space_id if row else None)
                or self.settings.aria_default_knowledge_space
            )
            project_name = manifest.project_name
            document_count = len(manifest.documents or [])
        except Exception:
            space_id = require_known_space(
                (row.space_id if row else None)
                or self.settings.aria_default_knowledge_space
            )
            project_name = row.project_name if row else engagement_id
            document_count = 0
            if row and isinstance(row.manifest, dict):
                raw = row.manifest.get("documents") or []
                if isinstance(raw, list):
                    document_count = len(raw)

        if not force_policy and not can_soft_delete_engagement(
            tier=tier,
            index_status=index_status,
            has_hard_refs=False,
            document_count=document_count,
        ):
            raise EngagementTrashConflict(
                "资料齐全且可检索的项目不支持一键删除，请联系管理员处理",
                ref_task_ids=[],
            )

        deleted_at = datetime.now(UTC).replace(microsecond=0)
        purge_after = deleted_at + timedelta(days=TRASH_RETENTION_DAYS)
        dest_dir = self.trash_root / space_id / engagement_id
        if dest_dir.exists():
            # Prior trash remnant: wipe then move.
            shutil.rmtree(dest_dir)

        dest_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(folder), str(dest_dir))

        meta = {
            "engagement_id": engagement_id,
            "space_id": space_id,
            "project_name": project_name,
            "deleted_at": deleted_at.isoformat().replace("+00:00", "Z"),
            "purge_after": purge_after.isoformat().replace("+00:00", "Z"),
            "deleted_by": deleted_by,
        }
        (dest_dir / TRASH_META_NAME).write_text(
            json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        if row is not None:
            self.db.delete(row)
            self.db.commit()

        ManpowerBaselinesStore(self.settings).remove_projects([engagement_id])

        return {
            "engagement_id": engagement_id,
            "space_id": space_id,
            "moved_to_trash": True,
            "purge_after": meta["purge_after"],
            "deleted_at": meta["deleted_at"],
            "needs_reindex": True,
        }

    def restore(
        self,
        engagement_id: str,
        *,
        restored_by: str | None = None,
        space_id: str | None = None,
    ) -> dict[str, Any]:
        engagement_id = (engagement_id or "").strip()
        space = require_known_space(
            space_id or self.settings.aria_default_knowledge_space
        )
        trash_folder = self.trash_root / space / engagement_id
        if not trash_folder.is_dir():
            # Search other spaces for convenience.
            found: Path | None = None
            if self.trash_root.is_dir():
                for candidate in self.trash_root.glob(f"*/{engagement_id}"):
                    if candidate.is_dir():
                        found = candidate
                        break
            if found is None:
                raise EngagementTrashNotFound(f"回收站中无此项目：{engagement_id}")
            trash_folder = found
            space = trash_folder.parent.name

        dest = self.kb_root / engagement_id
        if dest.exists():
            raise EngagementTrashConflict(
                f"知识库中已存在同编号项目：{engagement_id}",
                ref_task_ids=[],
            )

        meta_path = trash_folder / TRASH_META_NAME
        if meta_path.is_file():
            try:
                meta_path.unlink()
            except OSError:
                pass

        self.kb_root.mkdir(parents=True, exist_ok=True)
        shutil.move(str(trash_folder), str(dest))

        audit = EngagementAuditService(self.settings, self.db)
        row = audit.record_upload(dest, uploaded_by=restored_by)
        row.index_status = "pending"
        row.last_error = None
        self.repo.upsert(row)

        return {
            "engagement_id": engagement_id,
            "space_id": space,
            "restored": True,
            "index_status": "pending",
            "needs_reindex": True,
        }
