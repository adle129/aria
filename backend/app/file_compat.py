from __future__ import annotations

import re
import unicodedata
from pathlib import Path, PurePosixPath

_WINDOWS_DRIVE_RE = re.compile(r"^[a-zA-Z]:")


class FileCompatibilityError(ValueError):
    pass


def normalize_unicode(value: str) -> str:
    return unicodedata.normalize("NFC", value)


def normalize_filename(value: str) -> str:
    normalized = normalize_unicode(value.replace("\\", "/")).strip()
    name = PurePosixPath(normalized).name
    if not name or name in {".", ".."} or "/" in name:
        raise FileCompatibilityError("文件名非法")
    return name


def normalize_manifest_path(value: str) -> str:
    normalized = normalize_unicode(value.strip().replace("\\", "/"))
    path = PurePosixPath(normalized)
    if (
        not normalized
        or normalized.startswith(("/", "//"))
        or _WINDOWS_DRIVE_RE.match(normalized)
        or path.is_absolute()
        or path == PurePosixPath(".")
        or ".." in path.parts
    ):
        raise FileCompatibilityError(
            "manifest 路径须为项目目录内的 POSIX 相对路径"
        )
    return path.as_posix()


def resolve_case_insensitive(root: Path, relative_path: str) -> Path:
    normalized = normalize_manifest_path(relative_path)
    current = Path(root)
    for part in PurePosixPath(normalized).parts:
        if not current.is_dir():
            raise FileCompatibilityError(
                f"manifest 文件不存在：{normalized}"
            )
        matches = [
            child
            for child in current.iterdir()
            if normalize_unicode(child.name).casefold()
            == normalize_unicode(part).casefold()
        ]
        if len(matches) != 1:
            reason = "存在大小写歧义" if matches else "文件不存在"
            raise FileCompatibilityError(
                f"manifest 路径{reason}：{normalized}"
            )
        current = matches[0]
    if not current.is_file():
        raise FileCompatibilityError(
            f"manifest 文件不存在：{normalized}"
        )
    return current
