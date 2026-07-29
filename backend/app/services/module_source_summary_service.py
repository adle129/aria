"""Build cached module-scope summaries for quote source picking (R1-CHG08).

W1: static keyword placeholders + light text-hint extraction from already-loaded
similar_projects / comparison rows. Never issues live 3×9 retrieval.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.services.function_source_map_service import (
    QUOTE_FUNCTION_KEYS,
    resolve_in_scope_functions,
)
from app.services.module_keywords import DEFAULT_MODULE_KEYWORDS

_MAX_BULLETS = 4
_SNIPPET_LEN = 72


def build_module_source_summaries(
    *,
    rfq_modules: dict[str, Any] | None,
    comparison_table: dict[str, Any] | None,
    similar_projects: list[dict[str, Any]] | None = None,
    keywords: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return cache payload for ``RFQTask.module_source_summaries``."""
    table = keywords or DEFAULT_MODULE_KEYWORDS
    in_scope = resolve_in_scope_functions(rfq_modules)
    engagement_ids = _engagement_ids_from_comparison(comparison_table)
    text_by_eng = _texts_by_engagement(similar_projects, comparison_table)

    by_engagement: dict[str, dict[str, Any]] = {}
    for eng_id in engagement_ids:
        corpus = text_by_eng.get(eng_id, "")
        modules: dict[str, Any] = {}
        for fn in QUOTE_FUNCTION_KEYS:
            if fn not in in_scope:
                continue
            modules[fn] = _summarize_one(fn, corpus, table)
        by_engagement[eng_id] = modules

    return {
        "mode": "placeholder",
        "generated_at": datetime.now(UTC)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "in_scope": in_scope,
        "by_engagement": by_engagement,
        "note": "客户关键字表到位前为占位摘要；选源只读本缓存，不现场检索。",
    }


def _summarize_one(
    function_key: str,
    corpus: str,
    table: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    meta = table.get(function_key) or {}
    kws = [str(k).strip() for k in (meta.get("keywords") or []) if str(k).strip()]
    placeholders = [
        str(b).strip()
        for b in (meta.get("placeholder_bullets") or [])
        if str(b).strip()
    ][:_MAX_BULLETS]

    hits: list[str] = []
    lower = corpus.casefold()
    for kw in kws:
        idx = lower.find(kw.casefold())
        if idx < 0:
            continue
        start = max(0, idx - 12)
        end = min(len(corpus), idx + len(kw) + _SNIPPET_LEN)
        snippet = " ".join(corpus[start:end].split())
        if snippet and snippet not in hits:
            hits.append(snippet)
        if len(hits) >= _MAX_BULLETS:
            break

    if hits:
        return {
            "bullets": hits,
            "status": "hint",
            "source": "similar_text",
            "keywords_used": kws[:6],
        }
    if placeholders:
        return {
            "bullets": placeholders,
            "status": "placeholder",
            "source": "static_keywords",
            "keywords_used": kws[:6],
        }
    return {
        "bullets": ["暂无该模块工作范围摘要"],
        "status": "empty",
        "source": "none",
        "keywords_used": kws[:6],
    }


def _engagement_ids_from_comparison(
    comparison_table: dict[str, Any] | None,
) -> list[str]:
    if not isinstance(comparison_table, dict):
        return []
    projects = comparison_table.get("projects")
    if not isinstance(projects, list):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for proj in projects:
        if not isinstance(proj, dict):
            continue
        eng = str(proj.get("engagement_id") or "").strip()
        if not eng or eng in seen:
            continue
        seen.add(eng)
        out.append(eng)
    return out


def _texts_by_engagement(
    similar_projects: list[dict[str, Any]] | None,
    comparison_table: dict[str, Any] | None,
) -> dict[str, str]:
    out: dict[str, list[str]] = {}

    def _add(eng: str, *parts: Any) -> None:
        eng = str(eng or "").strip()
        if not eng:
            return
        bucket = out.setdefault(eng, [])
        for part in parts:
            text = str(part or "").strip()
            if text:
                bucket.append(text)

    for doc in similar_projects or []:
        if not isinstance(doc, dict):
            continue
        meta = doc.get("metadata") if isinstance(doc.get("metadata"), dict) else {}
        eng = str(doc.get("engagement_id") or meta.get("engagement_id") or "").strip()
        _add(eng, doc.get("content"), doc.get("summary"), meta.get("project_name"))

    if isinstance(comparison_table, dict):
        for proj in comparison_table.get("projects") or []:
            if not isinstance(proj, dict):
                continue
            eng = str(proj.get("engagement_id") or "").strip()
            _add(eng, proj.get("summary"), proj.get("source_doc"))
            dims = proj.get("dimensions")
            if isinstance(dims, dict):
                for key, cell in dims.items():
                    if isinstance(cell, dict):
                        _add(eng, key, cell.get("value"), cell.get("section_path"))
                    else:
                        _add(eng, key, cell)

    return {eng: "\n".join(parts) for eng, parts in out.items()}
