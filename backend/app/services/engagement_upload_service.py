from __future__ import annotations

import json
import re
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from app.config import Settings
from app.schemas.engagement import EngagementManifest
from app.services.engagement_completeness import classify_engagement
from app.services.engagement_manifest_service import infer_manifest_from_folder, resolve_manifest
from app.services.ingest.engagement_preview import build_engagement_preview


class EngagementUploadError(ValueError):
    pass


MAX_ENGAGEMENTS_PER_REQUEST = 5
MAX_ZIP_BYTES = 100 * 1024 * 1024
_ENGAGEMENT_ID_RE = re.compile(r"^[a-zA-Z0-9._-]{1,128}$")


def _validate_engagement_id(value: str) -> str:
    cleaned = value.strip()
    if not _ENGAGEMENT_ID_RE.match(cleaned):
        raise EngagementUploadError(f"invalid engagement_id: {value}")
    return cleaned


def _missing_from_preview(report: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    if not report.get("rfq"):
        missing.append("rfq")
    if not report.get("qa"):
        missing.append("qa")
    if not report.get("quote_baselines"):
        missing.append("quote_manpower")
    return missing


def _resolve_content_root(extracted: Path) -> Path:
    entries = [p for p in extracted.iterdir() if p.name not in {"__MACOSX"} and not p.name.startswith(".")]
    if len(entries) == 1 and entries[0].is_dir():
        return entries[0]
    return extracted


def _safe_extract_zip(zip_bytes: bytes, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp.write(zip_bytes)
        tmp_path = Path(tmp.name)
    try:
        with zipfile.ZipFile(tmp_path) as zf:
            for member in zf.namelist():
                target = (dest / member).resolve()
                if not str(target).startswith(str(dest.resolve())):
                    raise EngagementUploadError("ZIP 路径非法")
            zf.extractall(dest)
    finally:
        tmp_path.unlink(missing_ok=True)


class EngagementUploadService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.kb_root = Path(settings.knowledge_base_path)

    def upload_zip_pack(self, filename: str, content: bytes) -> dict[str, Any]:
        if len(content) > MAX_ZIP_BYTES:
            raise EngagementUploadError(f"{filename}: ZIP 超过 {MAX_ZIP_BYTES // (1024 * 1024)}MB 限制")
        if not filename.lower().endswith(".zip"):
            raise EngagementUploadError(f"{filename}: 须为 ZIP 文件")

        with tempfile.TemporaryDirectory() as tmp:
            extracted = Path(tmp) / "extract"
            _safe_extract_zip(content, extracted)
            content_root = _resolve_content_root(extracted)
            return self._finalize_folder(content_root, suggested_id=Path(filename).stem)

    def upload_loose_files(
        self,
        engagement_id: str,
        files: list[tuple[str, bytes]],
    ) -> dict[str, Any]:
        eid = _validate_engagement_id(engagement_id)
        if not files:
            raise EngagementUploadError("未上传任何文件")

        target = self.kb_root / eid
        if target.exists():
            raise EngagementUploadError(f"{eid}: 目录已存在，请先删除或更换 engagement_id")

        target.mkdir(parents=True, exist_ok=True)
        try:
            for name, data in files:
                safe_name = Path(name).name
                if not safe_name or safe_name.startswith("~$"):
                    continue
                (target / safe_name).write_bytes(data)
            manifest_path = target / "manifest.json"
            if not manifest_path.is_file():
                manifest = infer_manifest_from_folder(target)
                manifest_path.write_text(
                    json.dumps(manifest.model_dump(), ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
            return self._finalize_folder(target, suggested_id=eid)
        except Exception:
            shutil.rmtree(target, ignore_errors=True)
            raise

    def _finalize_folder(self, content_root: Path, *, suggested_id: str) -> dict[str, Any]:
        content_root = Path(content_root)
        manifest_path = content_root / "manifest.json"
        if manifest_path.is_file():
            manifest = resolve_manifest(content_root)
        else:
            default_id = content_root.name
            if default_id in {"extract", "tmp"} or not _ENGAGEMENT_ID_RE.match(default_id):
                default_id = Path(suggested_id).stem
            eid = _validate_engagement_id(default_id)
            manifest = infer_manifest_from_folder(content_root).model_copy(
                update={"engagement_id": eid, "project_name": eid.replace("_", " ").title()}
            )
            manifest_path.write_text(
                json.dumps(manifest.model_dump(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        engagement_id = _validate_engagement_id(manifest.engagement_id or suggested_id)
        target = self.kb_root / engagement_id

        if content_root.resolve() != target.resolve():
            if target.exists():
                raise EngagementUploadError(f"{engagement_id}: 目录已存在")
            self.kb_root.mkdir(parents=True, exist_ok=True)
            shutil.copytree(content_root, target)

        report = build_engagement_preview(target)
        missing = _missing_from_preview(report)
        completeness = classify_engagement(missing)
        rel_path = str(target.relative_to(self.kb_root)).replace("\\", "/")

        return {
            "engagement_id": engagement_id,
            "project_name": manifest.project_name,
            "status": "stored",
            "stored": True,
            "missing": missing,
            **completeness,
            "path": rel_path,
            "files": report.get("files_found") or [],
            "errors": report.get("errors") or [],
        }

    def upload_batch(
        self,
        zip_files: list[tuple[str, bytes]] | None = None,
        loose_files: list[tuple[str, bytes]] | None = None,
        engagement_id: str | None = None,
    ) -> dict[str, Any]:
        zip_files = zip_files or []
        loose_files = loose_files or []

        if zip_files and loose_files:
            raise EngagementUploadError("单次请求仅支持 ZIP 批量或单套散文件，不可混传")
        if not zip_files and not loose_files:
            raise EngagementUploadError("未上传任何文件")

        results: list[dict[str, Any]] = []
        if loose_files:
            if not engagement_id:
                raise EngagementUploadError("散文件上传须提供 engagement_id")
            results.append(self.upload_loose_files(engagement_id, loose_files))
        else:
            if len(zip_files) > MAX_ENGAGEMENTS_PER_REQUEST:
                raise EngagementUploadError(f"单次最多上传 {MAX_ENGAGEMENTS_PER_REQUEST} 套")
            for name, data in zip_files:
                results.append(self.upload_zip_pack(name, data))

        return {"packs": results, "uploaded": len(results)}
