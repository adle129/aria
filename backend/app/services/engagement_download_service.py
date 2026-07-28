"""Authorized download of engagement source documents (R1-CHG06)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.config import Settings
from app.repositories.engagement_repository import EngagementRepository
from app.services.engagement_document_service import ALLOWED_DOC_TYPES
from app.services.engagement_manifest_service import ManifestLoadError, resolve_manifest

DEFAULT_AUDIT_REL = "data/app/audit/knowledge_downloads.jsonl"


class EngagementDownloadError(ValueError):
    pass


class EngagementDownloadNotFound(EngagementDownloadError):
    pass


class EngagementDownloadService:
    def __init__(self, settings: Settings, db: Session):
        self.settings = settings
        self.db = db
        self.kb_root = Path(settings.knowledge_base_path)
        self.repo = EngagementRepository(db)

    def resolve_document(
        self,
        engagement_id: str,
        *,
        doc_type: str = "rfq",
    ) -> dict[str, Any]:
        """Return absolute path + metadata for a single doc_type file."""
        engagement_id = (engagement_id or "").strip()
        doc_type = (doc_type or "rfq").strip().casefold()
        if doc_type not in ALLOWED_DOC_TYPES:
            raise EngagementDownloadError(
                f"不支持的文件类型：{doc_type}（可选 rfq / qa / quote_manpower / summary）"
            )
        if (
            not engagement_id
            or engagement_id in {".", ".."}
            or "/" in engagement_id
            or "\\" in engagement_id
            or ".." in engagement_id
        ):
            raise EngagementDownloadNotFound(f"项目不存在：{engagement_id}")

        folder = (self.kb_root / engagement_id).resolve()
        try:
            folder.relative_to(self.kb_root.resolve())
        except ValueError as exc:
            raise EngagementDownloadNotFound(f"项目不存在：{engagement_id}") from exc
        if not folder.is_dir():
            raise EngagementDownloadNotFound(f"项目不存在：{engagement_id}")

        try:
            manifest = resolve_manifest(folder)
        except ManifestLoadError as exc:
            raise EngagementDownloadError(str(exc)) from exc

        matches = [d for d in (manifest.documents or []) if d.doc_type == doc_type]
        if not matches:
            raise EngagementDownloadNotFound(
                f"项目中无「{doc_type}」类文件：{engagement_id}"
            )

        rel = matches[0].path
        abs_path = (folder / rel).resolve()
        try:
            abs_path.relative_to(folder)
        except ValueError as exc:
            raise EngagementDownloadNotFound(
                f"项目中无「{doc_type}」类文件：{engagement_id}"
            ) from exc
        if not abs_path.is_file():
            raise EngagementDownloadNotFound(
                f"项目中无「{doc_type}」类文件：{engagement_id}"
            )

        download_name = matches[0].original_filename or abs_path.name
        return {
            "engagement_id": engagement_id,
            "doc_type": doc_type,
            "path": abs_path,
            "filename": Path(str(download_name)).name,
            "project_name": manifest.project_name,
            "media_type": _guess_media_type(abs_path.suffix),
        }

    @staticmethod
    def download_filename(
        base_filename: str,
        *,
        task_id: str | None = None,
        engagement_id: str | None = None,
        doc_type: str | None = None,
    ) -> str:
        """Compose browser download name.

        Prefer an ASCII-safe name so Content-Disposition uses plain ``filename=``
        (avoids filename* / CORS / parser edge cases). Include task_id when given.
        """
        original = Path(str(base_filename or "download")).name
        ext = Path(original).suffix or ""
        stem = Path(original).stem or "download"
        # Non-ASCII stems break some clients' Content-Disposition parsing; fall back.
        if not stem.isascii():
            eng = (engagement_id or "engagement").strip() or "engagement"
            dtype = (doc_type or "doc").strip() or "doc"
            stem = f"{eng}_{dtype}"
        tid = (task_id or "").strip()
        if tid:
            safe_tid = (
                tid.replace("/", "_")
                .replace("\\", "_")
                .replace("..", "_")
                .replace(":", "_")
            )
            if safe_tid and safe_tid not in {".", ".."}:
                stem = f"{stem}__task-{safe_tid}"
        return f"{stem}{ext}"

    def append_audit(
        self,
        *,
        engagement_id: str,
        doc_type: str,
        filename: str,
        user_id: str | None,
        username: str | None,
        task_id: str | None = None,
        outcome: str = "ok",
    ) -> None:
        audit_path = self._audit_path()
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        row = {
            "ts": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "engagement_id": engagement_id,
            "doc_type": doc_type,
            "filename": filename,
            "user_id": user_id,
            "username": username,
            "task_id": task_id,
            "outcome": outcome,
        }
        with audit_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    def _audit_path(self) -> Path:
        raw = (getattr(self.settings, "knowledge_download_audit_path", None) or "").strip()
        if raw:
            return Path(raw)
        return Path(DEFAULT_AUDIT_REL)


def _guess_media_type(suffix: str) -> str:
    s = (suffix or "").casefold()
    if s in {".doc", ".docx"}:
        return "application/msword" if s == ".doc" else (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
    if s == ".xlsx":
        return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    if s == ".pdf":
        return "application/pdf"
    if s in {".txt", ".md"}:
        return "text/plain; charset=utf-8"
    return "application/octet-stream"
