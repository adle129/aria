from __future__ import annotations

import json
import re
import shutil
import stat
import tempfile
import uuid
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

from app.config import Settings
from app.file_compat import normalize_filename, normalize_unicode
from app.schemas.engagement import EngagementManifest
from app.services.engagement_completeness import classify_engagement
from app.services.engagement_manifest_service import (
    ManifestLoadError,
    infer_manifest_from_folder,
    resolve_manifest,
)
from app.services.ingest.engagement_preview import build_engagement_preview


class EngagementUploadError(ValueError):
    pass


class EngagementUploadConflict(EngagementUploadError):
    pass


MAX_ENGAGEMENTS_PER_REQUEST = 5
_ENGAGEMENT_ID_RE = re.compile(r"^[a-zA-Z0-9._-]{1,128}$")
_WINDOWS_DRIVE_RE = re.compile(r"^[a-zA-Z]:")


def _validate_engagement_id(value: str) -> str:
    cleaned = value.strip()
    if not _ENGAGEMENT_ID_RE.match(cleaned):
        raise EngagementUploadError(f"invalid engagement_id: {value}")
    return cleaned


def _internal_filename(value: str) -> str:
    name = normalize_filename(value)
    return "manifest.json" if name.casefold() == "manifest.json" else name


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


def _safe_extract_zip(
    archive_path: Path,
    dest: Path,
    settings: Settings,
) -> dict[str, str]:
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path) as zf:
        members = zf.infolist()
        if len(members) > settings.upload_max_entries:
            raise EngagementUploadError(
                f"ZIP 条目数超过 {settings.upload_max_entries} 限制"
            )
        expanded_total = 0
        checked: list[tuple[zipfile.ZipInfo, PurePosixPath]] = []
        member_types: dict[str, bool] = {}
        collision_paths: dict[str, str] = {}
        original_names: dict[str, str] = {}
        for info in members:
            raw_name = info.filename
            normalized = normalize_unicode(raw_name.replace("\\", "/"))
            path = PurePosixPath(normalized)
            if path.name.casefold() == "manifest.json":
                path = PurePosixPath(*path.parts[:-1], "manifest.json")
                normalized = path.as_posix()
            mode = info.external_attr >> 16
            file_type = stat.S_IFMT(mode)
            if (
                not normalized
                or path == PurePosixPath(".")
                or normalized.startswith(("/", "//"))
                or _WINDOWS_DRIVE_RE.match(normalized)
                or path.is_absolute()
                or ".." in path.parts
                or stat.S_ISLNK(mode)
                or file_type not in {0, stat.S_IFREG, stat.S_IFDIR}
            ):
                raise EngagementUploadError(
                    f"ZIP 含非法路径或链接条目：{raw_name}"
                )
            path_key = path.as_posix()
            collision_key = path_key.casefold()
            if collision_key in collision_paths:
                raise EngagementUploadError(
                    f"ZIP 含大小写或 Unicode 冲突路径：{raw_name}"
                )
            collision_paths[collision_key] = path_key
            member_types[path_key] = info.is_dir()
            if not info.is_dir():
                original_names[path_key] = PurePosixPath(
                    raw_name.replace("\\", "/")
                ).name
            if info.file_size > settings.upload_max_single_file_bytes:
                raise EngagementUploadError(
                    f"ZIP 单文件超过限制：{raw_name}"
                )
            expanded_total += info.file_size
            if expanded_total > settings.upload_max_expanded_bytes:
                raise EngagementUploadError("ZIP 解压后总大小超过限制")
            if info.file_size:
                ratio = info.file_size / max(1, info.compress_size)
                if ratio > settings.upload_max_compression_ratio:
                    raise EngagementUploadError(
                        f"ZIP 压缩比异常：{raw_name}"
                    )
            checked.append((info, path))

        for path_key, is_directory in member_types.items():
            parts = PurePosixPath(path_key).parts
            for index in range(1, len(parts)):
                parent = PurePosixPath(*parts[:index]).as_posix()
                if parent in member_types and not member_types[parent]:
                    raise EngagementUploadError(
                        f"ZIP 文件与目录路径冲突：{path_key}"
                    )
            if not is_directory and any(
                other.startswith(f"{path_key}/")
                for other in member_types
            ):
                raise EngagementUploadError(
                    f"ZIP 文件与目录路径冲突：{path_key}"
                )

        root = dest.resolve()
        for info, path in checked:
            target = (dest / Path(*path.parts)).resolve()
            if not target.is_relative_to(root):
                raise EngagementUploadError(
                    f"ZIP 路径越界：{info.filename}"
                )
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as source, target.open("xb") as output:
                shutil.copyfileobj(
                    source,
                    output,
                    length=max(64 * 1024, settings.upload_stream_chunk_bytes),
                )
        return original_names


class EngagementUploadService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.kb_root = Path(settings.knowledge_base_path)
        self.staging_root = self.kb_root.parent / ".staging"

    @staticmethod
    def _write_inferred_manifest(
        folder: Path,
        engagement_id: str,
        *,
        original_names: dict[str, str] | None = None,
    ) -> None:
        manifest = infer_manifest_from_folder(
            folder,
            original_names=original_names,
        ).model_copy(
            update={
                "engagement_id": engagement_id,
                "project_name": engagement_id.replace("_", " ").title(),
            }
        )
        (folder / "manifest.json").write_text(
            json.dumps(
                manifest.model_dump(),
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    @staticmethod
    def _enrich_existing_manifest(
        folder: Path,
        original_names: dict[str, str],
    ) -> None:
        try:
            manifest = resolve_manifest(folder)
        except ManifestLoadError as exc:
            raise EngagementUploadError(
                f"manifest.json 校验失败：{exc}"
            ) from exc
        names_by_path = {
            normalize_unicode(path).casefold(): original
            for path, original in original_names.items()
        }
        documents = [
            document
            if document.original_filename
            else document.model_copy(
                update={
                    "original_filename": names_by_path.get(
                        normalize_unicode(document.path).casefold(),
                        PurePosixPath(document.path).name,
                    )
                }
            )
            for document in manifest.documents
        ]
        canonical = manifest.model_copy(
            update={"documents": documents}
        )
        (folder / "manifest.json").write_text(
            json.dumps(
                canonical.model_dump(),
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def upload_zip_pack(
        self,
        filename: str,
        content: bytes,
        *,
        replace_existing: bool = False,
    ) -> dict[str, Any]:
        if len(content) > self.settings.upload_max_archive_bytes:
            raise EngagementUploadError(
                f"{filename}: ZIP 超过 "
                f"{self.settings.upload_max_archive_bytes // (1024 * 1024)}MB 限制"
            )
        if not filename.lower().endswith(".zip"):
            raise EngagementUploadError(f"{filename}: 须为 ZIP 文件")

        self.staging_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=self.staging_root) as tmp:
            archive = Path(tmp) / "upload.zip"
            archive.write_bytes(content)
            return self.upload_zip_path(
                filename,
                archive,
                replace_existing=replace_existing,
            )

    def upload_zip_path(
        self,
        filename: str,
        archive_path: Path,
        *,
        replace_existing: bool = False,
    ) -> dict[str, Any]:
        if not filename.lower().endswith(".zip"):
            raise EngagementUploadError(f"{filename}: 须为 ZIP 文件")
        if archive_path.stat().st_size > self.settings.upload_max_archive_bytes:
            raise EngagementUploadError(
                f"{filename}: ZIP 超过 "
                f"{self.settings.upload_max_archive_bytes // (1024 * 1024)}MB 限制"
            )
        self.staging_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=self.staging_root) as tmp:
            extracted = Path(tmp) / "extract"
            try:
                original_names = _safe_extract_zip(
                    archive_path,
                    extracted,
                    self.settings,
                )
            except (
                zipfile.BadZipFile,
                NotImplementedError,
                RuntimeError,
            ) as exc:
                raise EngagementUploadError(
                    f"{filename}: ZIP 损坏、加密或压缩格式不受支持"
                ) from exc
            content_root = _resolve_content_root(extracted)
            relative_original_names: dict[str, str] = {}
            for path_key, original_name in original_names.items():
                extracted_path = extracted / Path(
                    *PurePosixPath(path_key).parts
                )
                if extracted_path.is_relative_to(content_root):
                    relative = extracted_path.relative_to(
                        content_root
                    ).as_posix()
                    relative_original_names[relative] = original_name
            if (content_root / "manifest.json").is_file():
                self._enrich_existing_manifest(
                    content_root,
                    relative_original_names,
                )
            else:
                default_id = content_root.name
                if (
                    default_id in {"extract", "tmp"}
                    or not _ENGAGEMENT_ID_RE.match(default_id)
                ):
                    default_id = Path(filename).stem
                self._write_inferred_manifest(
                    content_root,
                    _validate_engagement_id(default_id),
                    original_names=relative_original_names,
                )
            return self._finalize_folder(
                content_root,
                suggested_id=Path(filename).stem,
                replace_existing=replace_existing,
            )

    def upload_loose_files(
        self,
        engagement_id: str,
        files: list[tuple[str, bytes]],
        *,
        replace_existing: bool = False,
    ) -> dict[str, Any]:
        eid = _validate_engagement_id(engagement_id)
        if not files:
            raise EngagementUploadError("未上传任何文件")

        self.staging_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=self.staging_root) as tmp:
            source = Path(tmp) / eid
            source.mkdir()
            original_names: dict[str, str] = {}
            seen_names: set[str] = set()
            for name, data in files:
                safe_name = _internal_filename(name)
                if not safe_name or safe_name.startswith("~$"):
                    continue
                collision_key = safe_name.casefold()
                if collision_key in seen_names:
                    raise EngagementUploadError(
                        f"文件名大小写或 Unicode 冲突：{name}"
                    )
                seen_names.add(collision_key)
                original_names[safe_name] = PurePosixPath(
                    name.replace("\\", "/")
                ).name
                (source / safe_name).write_bytes(data)
            manifest_path = source / "manifest.json"
            if not manifest_path.is_file():
                self._write_inferred_manifest(
                    source,
                    eid,
                    original_names=original_names,
                )
            else:
                self._enrich_existing_manifest(
                    source,
                    original_names,
                )
            return self._finalize_folder(
                source,
                suggested_id=eid,
                replace_existing=replace_existing,
            )

    def upload_loose_paths(
        self,
        engagement_id: str,
        files: list[tuple[str, Path]],
        *,
        replace_existing: bool = False,
    ) -> dict[str, Any]:
        eid = _validate_engagement_id(engagement_id)
        if not files:
            raise EngagementUploadError("未上传任何文件")
        self.staging_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=self.staging_root) as tmp:
            source = Path(tmp) / eid
            source.mkdir()
            original_names: dict[str, str] = {}
            seen_names: set[str] = set()
            for name, file_path in files:
                safe_name = _internal_filename(name)
                if not safe_name or safe_name.startswith("~$"):
                    continue
                collision_key = safe_name.casefold()
                if collision_key in seen_names:
                    raise EngagementUploadError(
                        f"文件名大小写或 Unicode 冲突：{name}"
                    )
                seen_names.add(collision_key)
                original_names[safe_name] = PurePosixPath(
                    name.replace("\\", "/")
                ).name
                shutil.copyfile(file_path, source / safe_name)
            manifest_path = source / "manifest.json"
            if not manifest_path.is_file():
                self._write_inferred_manifest(
                    source,
                    eid,
                    original_names=original_names,
                )
            else:
                self._enrich_existing_manifest(
                    source,
                    original_names,
                )
            return self._finalize_folder(
                source,
                suggested_id=eid,
                replace_existing=replace_existing,
            )

    def _finalize_folder(
        self,
        content_root: Path,
        *,
        suggested_id: str,
        replace_existing: bool,
    ) -> dict[str, Any]:
        content_root = Path(content_root)
        manifest_path = content_root / "manifest.json"
        if manifest_path.is_file():
            try:
                manifest = resolve_manifest(content_root)
            except ManifestLoadError as exc:
                raise EngagementUploadError(
                    f"manifest.json 校验失败：{exc}"
                ) from exc
        else:
            default_id = content_root.name
            if default_id in {"extract", "tmp"} or not _ENGAGEMENT_ID_RE.match(default_id):
                default_id = Path(suggested_id).stem
            eid = _validate_engagement_id(default_id)
            self._write_inferred_manifest(content_root, eid)
            manifest = resolve_manifest(content_root)
        engagement_id = _validate_engagement_id(manifest.engagement_id or suggested_id)
        target = self.kb_root / engagement_id

        if target.exists() and not replace_existing:
            raise EngagementUploadConflict(
                f"{engagement_id}: 项目已存在；如需替换，请勾选“替换同 ID 项目”"
            )

        self.kb_root.mkdir(parents=True, exist_ok=True)
        self.staging_root.mkdir(parents=True, exist_ok=True)
        staging = self.staging_root / f"pack-{uuid.uuid4().hex}"
        backup = self.staging_root / f"backup-{uuid.uuid4().hex}"
        shutil.copytree(content_root, staging)
        report = build_engagement_preview(staging, manifest)
        missing = _missing_from_preview(report)
        completeness = classify_engagement(missing)
        if replace_existing and not completeness["indexable"]:
            shutil.rmtree(staging, ignore_errors=True)
            raise EngagementUploadError(
                f"{engagement_id}: 替换包缺少可解析 RFQ，已保留原项目"
            )

        moved_old = False
        try:
            if target.exists():
                target.rename(backup)
                moved_old = True
            staging.rename(target)
        except Exception:
            if moved_old and not target.exists() and backup.exists():
                backup.rename(target)
            raise
        finally:
            shutil.rmtree(staging, ignore_errors=True)
        if moved_old:
            shutil.rmtree(backup, ignore_errors=True)

        rel_path = str(target.relative_to(self.kb_root)).replace("\\", "/")

        return {
            "engagement_id": engagement_id,
            "project_name": manifest.project_name,
            "customer": manifest.customer,
            "year": manifest.year,
            "functions": list(manifest.functions or []),
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
        replace_existing: bool = False,
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
            results.append(
                self.upload_loose_files(
                    engagement_id,
                    loose_files,
                    replace_existing=replace_existing,
                )
            )
        else:
            if len(zip_files) > MAX_ENGAGEMENTS_PER_REQUEST:
                raise EngagementUploadError(f"单次最多上传 {MAX_ENGAGEMENTS_PER_REQUEST} 套")
            for name, data in zip_files:
                results.append(
                    self.upload_zip_pack(
                        name,
                        data,
                        replace_existing=replace_existing,
                    )
                )

        return {"packs": results, "uploaded": len(results)}

    def upload_batch_paths(
        self,
        *,
        zip_files: list[tuple[str, Path]] | None = None,
        loose_files: list[tuple[str, Path]] | None = None,
        engagement_id: str | None = None,
        replace_existing: bool = False,
    ) -> dict[str, Any]:
        zip_files = zip_files or []
        loose_files = loose_files or []
        if zip_files and loose_files:
            raise EngagementUploadError(
                "单次请求仅支持 ZIP 批量或单套散文件，不可混传"
            )
        if not zip_files and not loose_files:
            raise EngagementUploadError("未上传任何文件")
        if loose_files:
            if not engagement_id:
                raise EngagementUploadError(
                    "散文件上传须提供 engagement_id"
                )
            result = self.upload_loose_paths(
                engagement_id,
                loose_files,
                replace_existing=replace_existing,
            )
            return {"packs": [result], "uploaded": 1}
        if len(zip_files) > MAX_ENGAGEMENTS_PER_REQUEST:
            raise EngagementUploadError(
                f"单次最多上传 {MAX_ENGAGEMENTS_PER_REQUEST} 套"
            )
        results = [
            self.upload_zip_path(
                name,
                path,
                replace_existing=replace_existing,
            )
            for name, path in zip_files
        ]
        return {"packs": results, "uploaded": len(results)}
