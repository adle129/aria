"""Single-document upsert for an existing engagement (R1-CHG13)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.config import Settings
from app.file_compat import normalize_filename
from app.models.engagement import Engagement
from app.repositories.engagement_repository import EngagementRepository
from app.schemas.engagement import ManifestDocument
from app.services.engagement_completeness import classify_engagement
from app.services.engagement_content_hash import compute_engagement_content_hash
from app.services.engagement_manifest_service import (
    ManifestLoadError,
    metadata_fields_complete,
    resolve_manifest,
    write_manifest,
)
from app.services.ingest.engagement_preview import build_engagement_preview


class EngagementDocumentError(ValueError):
    pass


class EngagementDocumentNotFound(EngagementDocumentError):
    pass


class EngagementDocumentConflict(EngagementDocumentError):
    pass


ALLOWED_DOC_TYPES = frozenset({"rfq", "qa", "quote_manpower", "summary"})

DOC_TYPE_SUFFIXES: dict[str, frozenset[str]] = {
    "rfq": frozenset({".doc", ".docx"}),
    "qa": frozenset({".xlsx"}),
    "quote_manpower": frozenset({".xlsx"}),
    "summary": frozenset({".doc", ".docx", ".txt", ".md", ".pdf"}),
}


def _missing_from_preview(report: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    if not report.get("rfq"):
        missing.append("rfq")
    if not report.get("qa"):
        missing.append("qa")
    if not report.get("quote_baselines"):
        missing.append("quote_manpower")
    return missing


def _safe_engagement_folder(kb_root: Path, engagement_id: str) -> Path:
    cleaned = (engagement_id or "").strip()
    if (
        not cleaned
        or cleaned in {".", ".."}
        or "/" in cleaned
        or "\\" in cleaned
        or ".." in cleaned
    ):
        raise EngagementDocumentNotFound(f"项目不存在：{engagement_id}")
    root = kb_root.resolve()
    folder = (kb_root / cleaned).resolve()
    try:
        folder.relative_to(root)
    except ValueError as exc:
        raise EngagementDocumentNotFound(f"项目不存在：{engagement_id}") from exc
    if not folder.is_dir():
        raise EngagementDocumentNotFound(f"项目不存在：{engagement_id}")
    return folder


class EngagementDocumentService:
    def __init__(self, settings: Settings, db: Session):
        self.settings = settings
        self.db = db
        self.kb_root = Path(settings.knowledge_base_path)
        self.repo = EngagementRepository(db)

    def upsert_document(
        self,
        engagement_id: str,
        *,
        doc_type: str,
        filename: str,
        content: bytes,
        replace: bool = True,
    ) -> dict[str, Any]:
        doc_type = (doc_type or "").strip().casefold()
        if doc_type not in ALLOWED_DOC_TYPES:
            raise EngagementDocumentError(
                f"不支持的文件类型：{doc_type}（可选 rfq / qa / quote_manpower / summary）"
            )
        if not content:
            raise EngagementDocumentError("文件内容为空")

        folder = _safe_engagement_folder(self.kb_root, engagement_id)
        engagement_id = folder.name

        safe_name = normalize_filename(filename)
        if not safe_name or safe_name in {".", ".."}:
            raise EngagementDocumentError("文件名无效")
        suffix = Path(safe_name).suffix.casefold()
        allowed = DOC_TYPE_SUFFIXES[doc_type]
        if suffix not in allowed:
            raise EngagementDocumentError(
                f"「{doc_type}」仅支持 {', '.join(sorted(allowed))} 格式"
            )

        try:
            manifest = resolve_manifest(folder)
        except ManifestLoadError as exc:
            raise EngagementDocumentError(str(exc)) from exc

        existing = [d for d in manifest.documents if d.doc_type == doc_type]
        if existing and not replace:
            raise EngagementDocumentConflict(
                f"该项目已有「{doc_type}」类文件，如需覆盖请使用替换"
            )

        dest_name = self._destination_name(doc_type, safe_name, existing)
        dest_path = folder / dest_name

        # Remove previous files for this doc_type (replace semantics).
        for old in existing:
            old_path = folder / old.path
            if old_path.is_file() and old_path.resolve() != dest_path.resolve():
                try:
                    old_path.unlink()
                except OSError:
                    pass

        dest_path.write_bytes(content)

        new_docs = [d for d in manifest.documents if d.doc_type != doc_type]
        new_docs.append(
            ManifestDocument(
                path=dest_name,
                doc_type=doc_type,
                original_filename=safe_name,
            )
        )
        # Keep stable order: rfq, qa, quote_manpower, summary, others
        order = {"rfq": 0, "qa": 1, "quote_manpower": 2, "summary": 3}
        new_docs.sort(key=lambda d: (order.get(d.doc_type, 9), d.path))

        updated = manifest.model_copy(update={"documents": new_docs})
        write_manifest(folder, updated)

        report = build_engagement_preview(folder, updated)
        missing = _missing_from_preview(report)
        if not metadata_fields_complete(updated):
            missing = list(dict.fromkeys([*missing, "metadata"]))
        completeness = classify_engagement(missing)

        row = self.repo.get_by_id(engagement_id)
        rel = str(folder.relative_to(self.kb_root)).replace("\\", "/")
        content_hash = compute_engagement_content_hash(folder)
        if row is None:
            row = Engagement(
                id=engagement_id,
                project_name=updated.project_name,
                customer=updated.customer,
                vehicle_model=getattr(updated, "vehicle_model", None),
                year=updated.year,
                functions=list(updated.functions or []),
                folder_path=rel,
                manifest=updated.model_dump(),
                index_status="pending",
                tier=completeness["tier"],
                content_hash=content_hash,
                last_error=None,
            )
        else:
            row.project_name = updated.project_name
            row.customer = updated.customer
            row.vehicle_model = getattr(updated, "vehicle_model", None)
            row.year = updated.year
            row.functions = list(updated.functions or [])
            row.folder_path = rel
            row.manifest = updated.model_dump()
            row.tier = completeness["tier"]
            row.content_hash = content_hash
            row.index_status = "pending"
            row.last_error = None
        self.repo.upsert(row)

        return {
            "engagement_id": engagement_id,
            "doc_type": doc_type,
            "path": dest_name,
            "original_filename": safe_name,
            "tier": completeness["tier"],
            "metadata_complete": metadata_fields_complete(updated),
            "index_status": "pending",
            "needs_reindex": True,
            "missing": missing,
        }

    @staticmethod
    def _destination_name(
        doc_type: str,
        safe_name: str,
        existing: list[ManifestDocument],
    ) -> str:
        if existing:
            # Prefer keeping previous relative path basename when replacing.
            prev = Path(existing[0].path).name
            if Path(prev).suffix.casefold() == Path(safe_name).suffix.casefold():
                return prev
        # Prefer classifier-friendly names for new files.
        if doc_type == "rfq" and "rfq" not in safe_name.casefold():
            return f"RFQ_{safe_name}"
        if doc_type == "qa" and "q_a" not in safe_name.casefold():
            return f"Q_A_{safe_name}"
        if doc_type == "quote_manpower" and "报价" not in safe_name and "人力" not in safe_name:
            stem = Path(safe_name).stem
            return f"{stem}_人力报价.xlsx" if Path(safe_name).suffix else f"{safe_name}_人力报价.xlsx"
        return safe_name
