"""Knowledge Space identifiers (R1-CHG12 pre-embed)."""

from __future__ import annotations

import re

DEFAULT_KNOWLEDGE_SPACE = "quoting"
RESERVED_KNOWLEDGE_SPACES = frozenset({"quoting", "finance"})

_SPACE_RE = re.compile(r"^[a-z][a-z0-9_]{1,62}$")


class KnowledgeSpaceError(ValueError):
    pass


def normalize_space_id(value: str | None, *, default: str = DEFAULT_KNOWLEDGE_SPACE) -> str:
    """Return a valid space_id; blank/None → default."""
    cleaned = (value or "").strip().casefold()
    if not cleaned:
        return default
    if not _SPACE_RE.match(cleaned):
        raise KnowledgeSpaceError(f"无效的 space_id：{value}")
    return cleaned


def require_known_space(space_id: str | None, *, default: str = DEFAULT_KNOWLEDGE_SPACE) -> str:
    """Normalize and reject unknown reserved-product spaces beyond quoting/finance stub."""
    sid = normalize_space_id(space_id, default=default)
    if sid not in RESERVED_KNOWLEDGE_SPACES:
        raise KnowledgeSpaceError(f"未知的知识空间：{sid}")
    return sid
