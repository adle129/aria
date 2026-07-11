"""Resolve host vs Docker data directory paths."""

from __future__ import annotations

from pathlib import Path


def _normalize_posix(path: str) -> str:
    return path.replace("\\", "/").strip()


def resolve_data_path(raw: str) -> Path:
    """Map host ./backend/data/* or ./data/* to /app/data/* inside Docker."""
    text = _normalize_posix(raw)
    p = Path(text)
    if p.is_absolute():
        return p

    docker_data = Path("/app/data")
    if docker_data.is_dir():
        for prefix in ("./backend/data/", "backend/data/", "./data/", "data/"):
            if text.startswith(prefix):
                return (docker_data / text[len(prefix) :]).resolve()
        return (Path("/app") / p).resolve()

    return (Path.cwd() / p).resolve()


def resolve_task_file_path(stored: str, *, upload_dir: str | Path) -> Path:
    """Locate an uploaded RFQ file from DB path (supports legacy relative paths)."""
    raw = _normalize_posix(stored)
    p = Path(raw)
    if p.is_file():
        return p.resolve()

    upload_root = Path(upload_dir)
    candidates = [
        Path.cwd() / p,
        upload_root / p.name,
        resolve_data_path(raw),
    ]
    if raw.startswith("backend/data/"):
        candidates.append(Path("/app") / raw)
        candidates.append(resolve_data_path(f"./{raw}"))

    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        if candidate.is_file():
            return candidate.resolve()

    raise FileNotFoundError(stored)
