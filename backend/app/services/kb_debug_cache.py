"""Persistent preview cache for KB debug (survives per-request service instances)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.config import Settings

_MEMORY: dict[str, dict[str, Any]] = {}
_CACHE_NAME = "kb_debug_preview.json"


def corpus_key(settings: Settings) -> str:
    return str(Path(settings.validation_corpus_path).resolve())


def cache_path(settings: Settings) -> Path:
    return Path(settings.chroma_path).parent / "validation_reports" / _CACHE_NAME


def load_preview(settings: Settings) -> dict[str, Any] | None:
    key = corpus_key(settings)
    if key in _MEMORY:
        return _MEMORY[key]
    path = cache_path(settings)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if data.get("corpus_path") != key:
        return None
    _MEMORY[key] = data
    return data


def save_preview(settings: Settings, report: dict[str, Any]) -> None:
    key = corpus_key(settings)
    report = dict(report)
    report["corpus_path"] = key
    _MEMORY[key] = report
    path = cache_path(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def clear_preview(settings: Settings) -> None:
    key = corpus_key(settings)
    _MEMORY.pop(key, None)
    path = cache_path(settings)
    if path.exists():
        path.unlink()
