"""Move engagements/documents to trash; list / restore / purge (R1-CHG14/09)."""

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
from app.services.engagement_completeness import classify_engagement
from app.services.engagement_content_hash import compute_engagement_content_hash
from app.services.engagement_manifest_service import (
    ManifestLoadError,
    metadata_fields_complete,
    resolve_manifest,
    write_manifest,
)
from app.services.engagement_reference_service import (
    EngagementReferenceService,
    can_soft_delete_engagement,
)
from app.services.ingest.engagement_preview import build_engagement_preview
from app.services.knowledge_space import require_known_space
from app.services.manpower_baselines_store import ManpowerBaselinesStore

TRASH_RETENTION_DAYS = 30
TRASH_META_NAME = "trash_meta.json"
KIND_ENGAGEMENT = "engagement"
KIND_DOCUMENT = "document"


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


def engagement_trash_id(engagement_id: str) -> str:
    return f"eng__{(engagement_id or '').strip()}"


def document_trash_id(engagement_id: str, doc_type: str) -> str:
    return f"doc__{(engagement_id or '').strip()}__{(doc_type or '').strip().casefold()}"


def document_trash_dirname(engagement_id: str, doc_type: str) -> str:
    return f"doc__{(engagement_id or '').strip()}__{(doc_type or '').strip().casefold()}"


def parse_trash_id(trash_id: str) -> dict[str, str]:
    raw = (trash_id or "").strip()
    if raw.startswith("eng__"):
        eid = raw[len("eng__") :].strip()
        if not eid:
            raise EngagementTrashError("回收站编号无效")
        return {"kind": KIND_ENGAGEMENT, "engagement_id": eid}
    if raw.startswith("doc__"):
        rest = raw[len("doc__") :]
        # engagement_id may contain underscores; doc_type is last segment.
        if "__" not in rest:
            raise EngagementTrashError("回收站编号无效")
        eng_id, doc_type = rest.rsplit("__", 1)
        eng_id = eng_id.strip()
        doc_type = doc_type.strip().casefold()
        if not eng_id or not doc_type:
            raise EngagementTrashError("回收站编号无效")
        return {
            "kind": KIND_DOCUMENT,
            "engagement_id": eng_id,
            "doc_type": doc_type,
        }
    # Legacy L2 path: bare engagement_id
    if raw and raw not in {".", ".."} and "/" not in raw and "\\" not in raw:
        return {"kind": KIND_ENGAGEMENT, "engagement_id": raw}
    raise EngagementTrashError("回收站编号无效")


def _utc_now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def _iso(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _days_remaining(purge_after: datetime | None, *, now: datetime | None = None) -> int | None:
    if purge_after is None:
        return None
    current = now or _utc_now()
    delta = purge_after - current
    return max(0, int(delta.total_seconds() // 86400))


def _missing_from_preview(report: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    if not report.get("rfq"):
        missing.append("rfq")
    if not report.get("qa"):
        missing.append("qa")
    if not report.get("quote_baselines"):
        missing.append("quote_manpower")
    return missing


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

        deleted_at = _utc_now()
        purge_after = deleted_at + timedelta(days=TRASH_RETENTION_DAYS)
        tid = engagement_trash_id(engagement_id)
        dest_dir = self.trash_root / space_id / engagement_id
        if dest_dir.exists():
            shutil.rmtree(dest_dir)

        dest_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(folder), str(dest_dir))

        meta = {
            "trash_id": tid,
            "item_kind": KIND_ENGAGEMENT,
            "engagement_id": engagement_id,
            "space_id": space_id,
            "project_name": project_name,
            "display_name": project_name,
            "deleted_at": _iso(deleted_at),
            "purge_after": _iso(purge_after),
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
            "trash_id": tid,
            "space_id": space_id,
            "moved_to_trash": True,
            "purge_after": meta["purge_after"],
            "deleted_at": meta["deleted_at"],
            "needs_reindex": True,
        }

    def soft_delete_document(
        self,
        engagement_id: str,
        *,
        doc_type: str,
        deleted_by: str | None = None,
    ) -> dict[str, Any]:
        """Move one doc_type file into trash and update manifest (R1-CHG09)."""
        from app.services.engagement_document_service import ALLOWED_DOC_TYPES

        engagement_id = (engagement_id or "").strip()
        doc_type = (doc_type or "").strip().casefold()
        if doc_type not in ALLOWED_DOC_TYPES:
            raise EngagementTrashError(
                f"不支持的文件类型：{doc_type}（可选 rfq / qa / quote_manpower / summary）"
            )

        folder = self.kb_root / engagement_id
        if not folder.is_dir():
            raise EngagementTrashNotFound(f"项目不存在：{engagement_id}")

        try:
            manifest = resolve_manifest(folder)
        except ManifestLoadError as exc:
            raise EngagementTrashError(str(exc)) from exc

        matches = [d for d in (manifest.documents or []) if d.doc_type == doc_type]
        if not matches:
            raise EngagementTrashNotFound(
                f"项目中无「{doc_type}」类文件：{engagement_id}"
            )

        space_id = require_known_space(
            getattr(manifest, "space_id", None)
            or self.settings.aria_default_knowledge_space
        )
        warnings: list[str] = []
        if doc_type == "rfq" and len(matches) >= 1:
            other_rfq = [
                d for d in (manifest.documents or []) if d.doc_type == "rfq"
            ]
            if len(other_rfq) <= 1:
                warnings.append("last_rfq")

        deleted_at = _utc_now()
        purge_after = deleted_at + timedelta(days=TRASH_RETENTION_DAYS)
        tid = document_trash_id(engagement_id, doc_type)
        dest_dir = self.trash_root / space_id / document_trash_dirname(
            engagement_id, doc_type
        )
        if dest_dir.exists():
            shutil.rmtree(dest_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)

        moved_files: list[str] = []
        for doc in matches:
            src = folder / doc.path
            if not src.is_file():
                continue
            dest_name = Path(doc.path).name
            shutil.move(str(src), str(dest_dir / dest_name))
            moved_files.append(dest_name)

        if not moved_files:
            shutil.rmtree(dest_dir, ignore_errors=True)
            raise EngagementTrashNotFound(
                f"项目中无「{doc_type}」类文件：{engagement_id}"
            )

        meta = {
            "trash_id": tid,
            "item_kind": KIND_DOCUMENT,
            "engagement_id": engagement_id,
            "doc_type": doc_type,
            "space_id": space_id,
            "project_name": manifest.project_name,
            "display_name": moved_files[0],
            "files": moved_files,
            "original_documents": [
                {"path": d.path, "doc_type": d.doc_type, "original_filename": d.original_filename}
                for d in matches
            ],
            "deleted_at": _iso(deleted_at),
            "purge_after": _iso(purge_after),
            "deleted_by": deleted_by,
        }
        (dest_dir / TRASH_META_NAME).write_text(
            json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        new_docs = [d for d in (manifest.documents or []) if d.doc_type != doc_type]
        updated = manifest.model_copy(update={"documents": new_docs})
        write_manifest(folder, updated)

        report = build_engagement_preview(folder, updated)
        missing = _missing_from_preview(report)
        if not metadata_fields_complete(updated):
            missing = list(dict.fromkeys([*missing, "metadata"]))
        completeness = classify_engagement(missing)

        row = self.repo.get_by_id(engagement_id)
        content_hash = compute_engagement_content_hash(folder)
        if row is not None:
            row.manifest = updated.model_dump()
            row.tier = completeness["tier"]
            row.content_hash = content_hash
            row.index_status = "pending"
            row.last_error = None
            self.repo.upsert(row)

        if doc_type == "quote_manpower":
            ManpowerBaselinesStore(self.settings).remove_projects([engagement_id])

        return {
            "engagement_id": engagement_id,
            "doc_type": doc_type,
            "trash_id": tid,
            "space_id": space_id,
            "moved_to_trash": True,
            "purge_after": meta["purge_after"],
            "deleted_at": meta["deleted_at"],
            "tier": completeness["tier"],
            "metadata_complete": metadata_fields_complete(updated),
            "index_status": "pending",
            "needs_reindex": True,
            "warnings": warnings,
            "missing": missing,
        }

    def restore(
        self,
        engagement_id: str,
        *,
        restored_by: str | None = None,
        space_id: str | None = None,
    ) -> dict[str, Any]:
        return self.restore_item(
            engagement_trash_id(engagement_id),
            restored_by=restored_by,
            space_id=space_id,
        )

    def restore_item(
        self,
        trash_id: str,
        *,
        restored_by: str | None = None,
        space_id: str | None = None,
    ) -> dict[str, Any]:
        parsed = parse_trash_id(trash_id)
        if parsed["kind"] == KIND_ENGAGEMENT:
            return self._restore_engagement(
                parsed["engagement_id"],
                restored_by=restored_by,
                space_id=space_id,
            )
        return self._restore_document(
            parsed["engagement_id"],
            parsed["doc_type"],
            restored_by=restored_by,
            space_id=space_id,
        )

    def _restore_engagement(
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
            found: Path | None = None
            if self.trash_root.is_dir():
                for candidate in self.trash_root.glob(f"*/{engagement_id}"):
                    if candidate.is_dir() and not candidate.name.startswith("doc__"):
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
            "trash_id": engagement_trash_id(engagement_id),
            "item_kind": KIND_ENGAGEMENT,
            "engagement_id": engagement_id,
            "space_id": space,
            "restored": True,
            "index_status": "pending",
            "needs_reindex": True,
        }

    def _restore_document(
        self,
        engagement_id: str,
        doc_type: str,
        *,
        restored_by: str | None = None,
        space_id: str | None = None,
    ) -> dict[str, Any]:
        _ = restored_by
        engagement_id = (engagement_id or "").strip()
        doc_type = (doc_type or "").strip().casefold()
        space = require_known_space(
            space_id or self.settings.aria_default_knowledge_space
        )
        dirname = document_trash_dirname(engagement_id, doc_type)
        trash_folder = self.trash_root / space / dirname
        if not trash_folder.is_dir():
            found: Path | None = None
            if self.trash_root.is_dir():
                for candidate in self.trash_root.glob(f"*/{dirname}"):
                    if candidate.is_dir():
                        found = candidate
                        break
            if found is None:
                raise EngagementTrashNotFound(
                    f"回收站中无此文件：{engagement_id}/{doc_type}"
                )
            trash_folder = found
            space = trash_folder.parent.name

        dest_folder = self.kb_root / engagement_id
        if not dest_folder.is_dir():
            raise EngagementTrashConflict(
                f"目标项目不存在，无法恢复文件（请先恢复项目 {engagement_id}）",
                ref_task_ids=[],
            )

        try:
            manifest = resolve_manifest(dest_folder)
        except ManifestLoadError as exc:
            raise EngagementTrashError(str(exc)) from exc

        if any(d.doc_type == doc_type for d in (manifest.documents or [])):
            raise EngagementTrashConflict(
                f"项目已有「{doc_type}」类文件，请先删除或替换后再恢复",
                ref_task_ids=[],
            )

        meta = self._read_meta(trash_folder) or {}
        originals = meta.get("original_documents") or []
        files = meta.get("files") or []
        restored_docs = []
        if isinstance(originals, list) and originals:
            for item in originals:
                if not isinstance(item, dict):
                    continue
                name = Path(str(item.get("path") or "")).name
                src = trash_folder / name
                if not src.is_file():
                    continue
                dest_path = dest_folder / name
                if dest_path.exists():
                    dest_path = dest_folder / f"restored_{name}"
                shutil.move(str(src), str(dest_path))
                restored_docs.append(
                    {
                        "path": dest_path.name,
                        "doc_type": doc_type,
                        "original_filename": item.get("original_filename") or name,
                    }
                )
        else:
            for name in files:
                src = trash_folder / str(name)
                if not src.is_file():
                    continue
                dest_path = dest_folder / Path(str(name)).name
                if dest_path.exists():
                    dest_path = dest_folder / f"restored_{dest_path.name}"
                shutil.move(str(src), str(dest_path))
                restored_docs.append(
                    {
                        "path": dest_path.name,
                        "doc_type": doc_type,
                        "original_filename": dest_path.name,
                    }
                )

        if not restored_docs:
            raise EngagementTrashNotFound(
                f"回收站中无此文件：{engagement_id}/{doc_type}"
            )

        from app.schemas.engagement import ManifestDocument

        new_docs = list(manifest.documents or [])
        for d in restored_docs:
            new_docs.append(
                ManifestDocument(
                    path=d["path"],
                    doc_type=d["doc_type"],
                    original_filename=d["original_filename"],
                )
            )
        order = {"rfq": 0, "qa": 1, "quote_manpower": 2, "summary": 3}
        new_docs.sort(key=lambda d: (order.get(d.doc_type, 9), d.path))
        updated = manifest.model_copy(update={"documents": new_docs})
        write_manifest(dest_folder, updated)

        report = build_engagement_preview(dest_folder, updated)
        missing = _missing_from_preview(report)
        if not metadata_fields_complete(updated):
            missing = list(dict.fromkeys([*missing, "metadata"]))
        completeness = classify_engagement(missing)

        row = self.repo.get_by_id(engagement_id)
        content_hash = compute_engagement_content_hash(dest_folder)
        if row is not None:
            row.manifest = updated.model_dump()
            row.tier = completeness["tier"]
            row.content_hash = content_hash
            row.index_status = "pending"
            row.last_error = None
            self.repo.upsert(row)

        shutil.rmtree(trash_folder, ignore_errors=True)

        return {
            "trash_id": document_trash_id(engagement_id, doc_type),
            "item_kind": KIND_DOCUMENT,
            "engagement_id": engagement_id,
            "doc_type": doc_type,
            "space_id": space,
            "restored": True,
            "index_status": "pending",
            "needs_reindex": True,
            "tier": completeness["tier"],
        }

    def list_items(self, *, space_id: str | None = None) -> list[dict[str, Any]]:
        space = require_known_space(
            space_id or self.settings.aria_default_knowledge_space
        )
        root = self.trash_root / space
        if not root.is_dir():
            return []
        now = _utc_now()
        items: list[dict[str, Any]] = []
        for child in sorted(root.iterdir(), key=lambda p: p.name):
            if not child.is_dir():
                continue
            meta = self._read_meta(child) or {}
            kind = meta.get("item_kind") or (
                KIND_DOCUMENT if child.name.startswith("doc__") else KIND_ENGAGEMENT
            )
            purge_after = _parse_iso(meta.get("purge_after"))
            deleted_at = _parse_iso(meta.get("deleted_at"))
            if kind == KIND_DOCUMENT:
                parsed = parse_trash_id(
                    meta.get("trash_id")
                    or document_trash_id(
                        str(meta.get("engagement_id") or ""),
                        str(meta.get("doc_type") or child.name.rsplit("__", 1)[-1]),
                    )
                )
                tid = meta.get("trash_id") or document_trash_id(
                    parsed["engagement_id"], parsed["doc_type"]
                )
                items.append(
                    {
                        "trash_id": tid,
                        "item_kind": KIND_DOCUMENT,
                        "engagement_id": parsed["engagement_id"],
                        "doc_type": parsed.get("doc_type"),
                        "project_name": meta.get("project_name"),
                        "display_name": meta.get("display_name")
                        or meta.get("files", [None])[0],
                        "space_id": space,
                        "deleted_at": meta.get("deleted_at"),
                        "purge_after": meta.get("purge_after"),
                        "days_remaining": _days_remaining(purge_after, now=now),
                        "deleted_by": meta.get("deleted_by"),
                    }
                )
            else:
                eid = str(meta.get("engagement_id") or child.name)
                tid = meta.get("trash_id") or engagement_trash_id(eid)
                items.append(
                    {
                        "trash_id": tid,
                        "item_kind": KIND_ENGAGEMENT,
                        "engagement_id": eid,
                        "doc_type": None,
                        "project_name": meta.get("project_name"),
                        "display_name": meta.get("display_name")
                        or meta.get("project_name")
                        or eid,
                        "space_id": space,
                        "deleted_at": meta.get("deleted_at"),
                        "purge_after": meta.get("purge_after"),
                        "days_remaining": _days_remaining(purge_after, now=now),
                        "deleted_by": meta.get("deleted_by"),
                    }
                )
            _ = deleted_at  # reserved for future sorting
        items.sort(key=lambda r: r.get("deleted_at") or "", reverse=True)
        return items

    def purge_item(self, trash_id: str) -> dict[str, Any]:
        folder = self._resolve_trash_folder(trash_id)
        meta = self._read_meta(folder) or {}
        parsed = parse_trash_id(trash_id)
        shutil.rmtree(folder, ignore_errors=True)
        return {
            "trash_id": meta.get("trash_id") or trash_id,
            "item_kind": parsed["kind"],
            "engagement_id": parsed["engagement_id"],
            "doc_type": parsed.get("doc_type"),
            "purged": True,
        }

    def purge_expired(self, *, space_id: str | None = None) -> dict[str, Any]:
        space = require_known_space(
            space_id or self.settings.aria_default_knowledge_space
        )
        root = self.trash_root / space
        if not root.is_dir():
            return {"space_id": space, "purged_count": 0, "purged": []}
        now = _utc_now()
        purged: list[str] = []
        for child in list(root.iterdir()):
            if not child.is_dir():
                continue
            meta = self._read_meta(child) or {}
            purge_after = _parse_iso(meta.get("purge_after"))
            if purge_after is None or purge_after > now:
                continue
            tid = meta.get("trash_id") or child.name
            shutil.rmtree(child, ignore_errors=True)
            purged.append(str(tid))
        return {"space_id": space, "purged_count": len(purged), "purged": purged}

    def _resolve_trash_folder(self, trash_id: str) -> Path:
        parsed = parse_trash_id(trash_id)
        if parsed["kind"] == KIND_ENGAGEMENT:
            eid = parsed["engagement_id"]
            if self.trash_root.is_dir():
                direct = list(self.trash_root.glob(f"*/{eid}"))
                for candidate in direct:
                    if candidate.is_dir() and not candidate.name.startswith("doc__"):
                        return candidate
            raise EngagementTrashNotFound(f"回收站中无此条目：{trash_id}")
        dirname = document_trash_dirname(parsed["engagement_id"], parsed["doc_type"])
        if self.trash_root.is_dir():
            for candidate in self.trash_root.glob(f"*/{dirname}"):
                if candidate.is_dir():
                    return candidate
        raise EngagementTrashNotFound(f"回收站中无此条目：{trash_id}")

    @staticmethod
    def _read_meta(folder: Path) -> dict[str, Any] | None:
        path = folder / TRASH_META_NAME
        if not path.is_file():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return data if isinstance(data, dict) else None
