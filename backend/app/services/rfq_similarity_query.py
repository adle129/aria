"""Build retrieval queries for RFQ → historical similar-project matching."""

from __future__ import annotations

from pathlib import Path
from typing import Any

_PLACEHOLDER_NAMES = frozenset({"", "未知", "未命名项目", "unknown", "n/a", "na"})

# Generic RFQ outline titles that add noise without discriminating projects.
_GENERIC_SCOPE_TITLES = frozenset(
    {
        "工作内容及要求",
        "工作内容",
        "工作范围",
        "项目概述",
        "概述",
        "目的",
        "目的与范围",
        "范围",
        "总则",
        "说明",
        "附录",
        "目录",
        "scope of work",
        "scope",
        "overview",
        "introduction",
        "general",
        "contents",
    }
)


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text in {"—", "-", "–"}:
        return None
    if text.casefold() in _PLACEHOLDER_NAMES:
        return None
    return text


def _is_generic_scope_title(title: str) -> bool:
    key = title.casefold().strip()
    if key in _GENERIC_SCOPE_TITLES:
        return True
    # Very short numeric-only section labels (e.g. "4", "4.1") are weak alone.
    if len(key) <= 3 and any(ch.isdigit() for ch in key):
        return True
    return False


def _dedupe_append(parts: list[str], seen: set[str], value: str | None) -> None:
    if not value:
        return
    key = value.casefold()
    if key in seen:
        return
    seen.add(key)
    parts.append(value)


def build_rfq_similarity_query(
    rfq_modules: dict[str, Any] | None,
    *,
    draft: dict[str, Any] | None = None,
    file_name: str | None = None,
    max_chars: int = 800,
    max_scope_titles: int = 12,
    max_dimension_phrases: int = 16,
) -> str:
    """Compose a retrieval query richer than project_name / file_name alone.

    Order (highest signal first):
    project_name → customer → platform → functions → development_scope titles →
    confirmed in_scope dimension names / work_content → file stem fallback.

    Generic outline titles are skipped so the embedding is not diluted.
    """
    modules = rfq_modules if isinstance(rfq_modules, dict) else {}
    parts: list[str] = []
    seen: set[str] = set()

    name = _clean(modules.get("project_name"))
    if name:
        _dedupe_append(parts, seen, name)
    else:
        stem = _clean(Path(file_name).stem) if file_name else None
        _dedupe_append(parts, seen, stem)

    _dedupe_append(parts, seen, _clean(modules.get("customer")))
    _dedupe_append(parts, seen, _clean(modules.get("platform_type")))

    functions = [
        f
        for f in (_clean(x) for x in (modules.get("functions_in_scope") or []))
        if f
    ]
    if functions:
        _dedupe_append(parts, seen, " ".join(functions[:8]))

    scope_count = 0
    for item in modules.get("development_scope") or []:
        if scope_count >= max_scope_titles:
            break
        if not isinstance(item, dict):
            continue
        title = _clean(item.get("title"))
        if not title or _is_generic_scope_title(title):
            continue
        before = len(parts)
        _dedupe_append(parts, seen, title)
        if len(parts) > before:
            scope_count += 1

    dim_count = 0
    if isinstance(draft, dict):
        rows = list(draft.get("items") or []) + list(draft.get("custom_items") or [])
        for item in rows:
            if dim_count >= max_dimension_phrases:
                break
            if not isinstance(item, dict) or item.get("in_scope") is not True:
                continue
            for key in ("name", "work_content"):
                if dim_count >= max_dimension_phrases:
                    break
                phrase = _clean(item.get(key))
                if not phrase:
                    continue
                before = len(parts)
                _dedupe_append(parts, seen, phrase)
                if len(parts) > before:
                    dim_count += 1

    query = " ".join(parts).strip()
    if not query and file_name:
        query = Path(file_name).name
    if len(query) > max_chars:
        query = query[: max_chars - 1].rstrip() + "…"
    return query
