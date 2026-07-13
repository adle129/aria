"""Structured overlap scoring for RFQ → historical project ranking."""

from __future__ import annotations

from typing import Any


def _norm(value: Any) -> str:
    return str(value or "").strip().casefold()


def _token_set(values: list[Any] | None) -> set[str]:
    out: set[str] = set()
    for value in values or []:
        text = _norm(value)
        if text and text not in {"—", "-", "–", "未知", "未命名项目"}:
            out.add(text)
    return out


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def _scope_titles_from_modules(rfq_modules: dict[str, Any] | None) -> set[str]:
    titles: set[str] = set()
    modules = rfq_modules if isinstance(rfq_modules, dict) else {}
    for item in modules.get("development_scope") or []:
        if isinstance(item, dict):
            title = _norm(item.get("title"))
            if title:
                titles.add(title)
    return titles


def _in_scope_phrases(draft: dict[str, Any] | None) -> set[str]:
    phrases: set[str] = set()
    if not isinstance(draft, dict):
        return phrases
    rows = list(draft.get("items") or []) + list(draft.get("custom_items") or [])
    for item in rows:
        if not isinstance(item, dict) or item.get("in_scope") is not True:
            continue
        for key in ("name", "work_content"):
            text = _norm(item.get(key))
            if text and text not in {"—", "-", "–"}:
                phrases.add(text)
    return phrases


def _section_path_phrases(section_paths: list[str] | None) -> set[str]:
    phrases: set[str] = set()
    for path in section_paths or []:
        text = str(path or "").strip()
        if not text:
            continue
        for part in text.replace(">", "/").split("/"):
            piece = _norm(part)
            if piece:
                phrases.add(piece)
        phrases.add(_norm(text))
    return phrases


def _partial_name_score(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    if left == right:
        return 1.0
    if left in right or right in left:
        return 0.75
    left_tokens = {t for t in left.replace("-", " ").split() if len(t) > 1}
    right_tokens = {t for t in right.replace("-", " ").split() if len(t) > 1}
    return jaccard(left_tokens, right_tokens)


def structured_similarity_score(
    rfq_modules: dict[str, Any] | None,
    candidate_meta: dict[str, Any] | None,
    *,
    draft: dict[str, Any] | None = None,
    section_paths: list[str] | None = None,
) -> float:
    """Return 0..1 structured overlap between current RFQ and a historical project.

    Weights: functions 0.35 · scope/path 0.30 · project_name 0.20 · customer/platform 0.15
    """
    modules = rfq_modules if isinstance(rfq_modules, dict) else {}
    meta = candidate_meta if isinstance(candidate_meta, dict) else {}

    current_funcs = _token_set(list(modules.get("functions_in_scope") or []))
    cand_funcs = _token_set(list(meta.get("functions") or []))
    func_score = jaccard(current_funcs, cand_funcs)

    scope_titles = _scope_titles_from_modules(modules) | _in_scope_phrases(draft)
    path_phrases = _section_path_phrases(section_paths)
    # Also allow candidate project_name tokens to soft-match scope phrases.
    path_phrases |= _token_set([meta.get("project_name")])
    scope_score = jaccard(scope_titles, path_phrases) if scope_titles else 0.0

    name_score = _partial_name_score(
        _norm(modules.get("project_name")),
        _norm(meta.get("project_name")),
    )

    customer_score = 1.0 if (
        _norm(modules.get("customer"))
        and _norm(modules.get("customer")) == _norm(meta.get("customer"))
    ) else 0.0
    platform = _norm(modules.get("platform_type"))
    platform_blob = " ".join(
        [
            _norm(meta.get("project_name")),
            _norm(meta.get("customer")),
            " ".join(_norm(x) for x in (meta.get("functions") or [])),
        ]
    )
    platform_score = 1.0 if platform and platform in platform_blob else 0.0
    identity_score = max(customer_score, platform_score * 0.8)

    score = (
        0.35 * func_score
        + 0.30 * scope_score
        + 0.20 * name_score
        + 0.15 * identity_score
    )
    return round(min(1.0, max(0.0, score)), 3)


def fuse_similarity_scores(
    vector_score: float,
    structured_score: float,
    *,
    vector_weight: float = 0.65,
) -> float:
    """Linear fusion; vector_weight in (0, 1]."""
    vw = min(1.0, max(0.0, float(vector_weight)))
    fused = vw * float(vector_score or 0.0) + (1.0 - vw) * float(structured_score or 0.0)
    return round(min(1.0, max(0.0, fused)), 3)


def rerank_similar_groups(
    groups: list[dict[str, Any]],
    rfq_modules: dict[str, Any] | None,
    *,
    draft: dict[str, Any] | None = None,
    top_k: int = 3,
    vector_weight: float = 0.65,
) -> list[dict[str, Any]]:
    """Re-rank engagement groups by fused vector + structured scores."""
    ranked: list[dict[str, Any]] = []
    for group in groups:
        meta = dict(group.get("metadata") or {})
        if group.get("engagement_id") and not meta.get("engagement_id"):
            meta["engagement_id"] = group.get("engagement_id")
        if group.get("project_name") and not meta.get("project_name"):
            meta["project_name"] = group.get("project_name")
        section_paths = [
            str((hit.get("metadata") or {}).get("section_path") or "")
            for hit in (group.get("hits") or [])
            if (hit.get("metadata") or {}).get("section_path")
        ]
        vector_score = float(group.get("similarity_score") or 0.0)
        structured = structured_similarity_score(
            rfq_modules,
            meta,
            draft=draft,
            section_paths=section_paths,
        )
        fused = fuse_similarity_scores(
            vector_score, structured, vector_weight=vector_weight
        )
        enriched = dict(group)
        enriched["vector_score"] = round(vector_score, 3)
        enriched["structured_score"] = structured
        enriched["similarity_score"] = fused
        ranked.append(enriched)

    ranked.sort(key=lambda g: float(g.get("similarity_score") or 0.0), reverse=True)
    return ranked[: max(1, top_k)]
