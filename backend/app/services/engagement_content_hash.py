"""Compute engagement content fingerprints for audit and incremental indexing."""

from __future__ import annotations

import hashlib
from pathlib import Path

from app.config import get_settings

_PARSER_VERSION = "engagement_preview_v1"
_CHUNK_SCHEMA_VERSION = "rfqa_v1"


def compute_engagement_content_hash(folder: Path) -> str:
    """Stable hash from file bytes, names, parser and chunk schema versions."""
    settings = get_settings()
    folder = Path(folder)
    digest = hashlib.sha256()
    for path in sorted(
        p for p in folder.rglob("*") if p.is_file() and not p.name.startswith("~$")
    ):
        rel = path.relative_to(folder).as_posix().casefold()
        digest.update(rel.encode("utf-8"))
        digest.update(path.read_bytes())
    digest.update(_PARSER_VERSION.encode("utf-8"))
    digest.update(_CHUNK_SCHEMA_VERSION.encode("utf-8"))
    digest.update(settings.embedding_model.encode("utf-8"))
    return digest.hexdigest()
