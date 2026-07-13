"""Layer-2 section alignment: map in_scope dimensions to historical RFQ leaf chunks.

P0 fills comparison_table dimensions only; does not rewrite Layer-1 project ranking.
"""

from __future__ import annotations

import re
from typing import Any

_NUMBERING_RE = re.compile(
    r"^(?:"
    r"\d+(?:\.\d+)*\.?\s*"
    r"|[一二三四五六七八九十百千]+[、．.]\s*"
    r"|[（(][一二三四五六七八九十\d]+[）)]\s*"
    r"|[A-Za-z]\d*(?:\.\d+)*\.?\s*"
    r")"
)
_WS_RE = re.compile(r"\s+")
_PUNCT_RE = re.compile(r"[，。、；：:（）()【】\[\]<>《》\"'·•/\\|]+")

VALUE_MAX_CHARS = 400
TITLE_ALIGN_MIN = 0.35
CONTENT_MATCH_TRUE = 0.45
CONTENT_MATCH_FALSE = 0.20


def normalize_title(value: Any) -> str:
    text = str(value or "").strip().casefold()
    if not text:
        return ""
    text = text.replace("＞", ">").replace("／", "/")
    text = _NUMBERING_RE.sub("", text)
    text = _PUNCT_RE.sub(" ", text)
    text = _WS_RE.sub(" ", text).strip()
    return text


def _title_tokens(value: Any) -> set[str]:
    raw = str(value or "").strip()
    if not raw:
        return set()
    segments = re.split(r"[>/＞]+", raw) if re.search(r"[>/＞]", raw) else [raw]
    tokens: set[str] = set()
    for segment in segments:
        norm = normalize_title(segment)
        if not norm:
            continue
        for part in re.split(r"\s+", norm):
            piece = part.strip()
            if len(piece) >= 2:
                tokens.add(piece)
        if len(norm) >= 2:
            tokens.add(norm)
    return tokens


def title_overlap_score(left: Any, right: Any) -> float:
    a = _title_tokens(left)
    b = _title_tokens(right)
    if not a or not b:
        return 0.0
    if a & b:
        if a.issubset(b) or b.issubset(a):
            return 1.0
        inter = len(a & b)
        union = len(a | b)
        jacc = inter / union if union else 0.0
        return max(jacc, 0.75)
    la, lb = normalize_title(left), normalize_title(right)
    if la and lb and (la in lb or lb in la):
        return 0.7
    for ta in a:
        for tb in b:
            if len(ta) >= 2 and len(tb) >= 2 and (ta in tb or tb in ta):
                return 0.65
    return 0.0


def _content_body(chunk: dict[str, Any]) -> str:
    content = str(chunk.get("content") or "")
    meta = chunk.get("metadata") or {}
    path = str(meta.get("section_path") or "").strip()
    if path and content.startswith(path):
        rest = content[len(path) :].lstrip("\n")
        return rest or content
    if "\n" in content:
        first, _, rest = content.partition("\n")
        chapter = str(meta.get("chunk_chapter") or "")
        if rest and (first == path or (chapter and first.endswith(chapter))):
            return rest
    return content


def content_overlap_score(left: Any, right: Any) -> float:
    a = _WS_RE.sub(" ", str(left or "").strip().casefold())
    b = _WS_RE.sub(" ", str(right or "").strip().casefold())
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    if a in b or b in a:
        shorter = min(len(a), len(b))
        longer = max(len(a), len(b))
        return min(1.0, 0.5 + 0.5 * (shorter / longer))

    def _tok(text: str) -> set[str]:
        out: set[str] = set()
        for m in re.finditer(r"[a-z0-9_]{2,}|[\u4e00-\u9fff]{1,}", text):
            t = m.group(0)
            if len(t) == 1 and "\u4e00" <= t <= "\u9fff":
                continue
            if len(t) >= 2 and "\u4e00" <= t[0] <= "\u9fff":
                for i in range(len(t) - 1):
                    out.add(t[i : i + 2])
            else:
                out.add(t)
        return out

    ta, tb = _tok(a), _tok(b)
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    union = len(ta | tb)
    return inter / union if union else 0.0


def _chunk_title_blob(chunk: dict[str, Any]) -> str:
    meta = chunk.get("metadata") or {}
    parts = [
        meta.get("section_path"),
        meta.get("chunk_chapter"),
        " ".join(str(p) for p in (meta.get("parent_titles") or [])),
    ]
    return " > ".join(str(p) for p in parts if p)


def _in_scope_items(draft: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(draft, dict):
        return []
    rows = list(draft.get("items") or []) + list(draft.get("custom_items") or [])
    return [
        item
        for item in rows
        if isinstance(item, dict) and item.get("in_scope") is True and item.get("name")
    ]


def align_dimension_to_chunks(
    dim_name: str,
    work_content: str,
    chunks: list[dict[str, Any]],
    *,
    title_min: float = TITLE_ALIGN_MIN,
    value_max_chars: int = VALUE_MAX_CHARS,
) -> dict[str, Any]:
    unknown = {
        "value": "未知",
        "match": None,
        "section_path": None,
        "chunk_id": None,
        "content_score": 0.0,
    }
    if not chunks:
        return unknown

    scored: list[tuple[float, float, dict[str, Any]]] = []
    for chunk in chunks:
        title_score = title_overlap_score(dim_name, _chunk_title_blob(chunk))
        if title_score < title_min:
            continue
        body = _content_body(chunk)
        content_score = content_overlap_score(work_content, body) if work_content else title_score
        scored.append((title_score, content_score, chunk))

    if not scored:
        return unknown

    scored.sort(key=lambda row: (row[1], row[0]), reverse=True)
    best_title, best_content, best = scored[0]
    meta = best.get("metadata") or {}
    body = _content_body(best).strip()
    if not body:
        return unknown
    value = body if len(body) <= value_max_chars else body[:value_max_chars].rstrip() + "…"

    if best_content >= CONTENT_MATCH_TRUE or (
        best_title >= 0.7 and best_content >= CONTENT_MATCH_FALSE
    ):
        match: bool | None = True
    elif best_content < CONTENT_MATCH_FALSE and best_title < 0.55:
        match = False
    else:
        match = None

    return {
        "value": value,
        "match": match,
        "section_path": meta.get("section_path") or None,
        "chunk_id": best.get("chunk_id") or meta.get("chunk_id"),
        "content_score": round(float(best_content), 3),
    }


def align_sections_for_engagement(
    draft: dict[str, Any] | None,
    chunks: list[dict[str, Any]],
    *,
    title_min: float = TITLE_ALIGN_MIN,
    value_max_chars: int = VALUE_MAX_CHARS,
) -> dict[str, Any]:
    items = _in_scope_items(draft)
    dimensions: dict[str, dict[str, Any]] = {}
    content_scores: list[float] = []
    aligned = 0

    for item in items:
        name = str(item.get("name") or "")
        work = str(item.get("work_content") or "")
        cell = align_dimension_to_chunks(
            name,
            work,
            chunks,
            title_min=title_min,
            value_max_chars=value_max_chars,
        )
        dimensions[name] = cell
        if cell.get("value") and cell["value"] != "未知":
            aligned += 1
            content_scores.append(float(cell.get("content_score") or 0.0))

    total = len(items) or 1
    coverage = aligned / total if items else 0.0
    content_mean = sum(content_scores) / len(content_scores) if content_scores else 0.0
    return {
        "dimensions": dimensions,
        "section_coverage": round(coverage, 3),
        "section_content_mean": round(content_mean, 3),
        "aligned_count": aligned,
    }


def apply_section_align_to_groups(
    groups: list[dict[str, Any]],
    draft: dict[str, Any] | None,
    *,
    fetch_chunks,
    top_k: int = 3,
    rerank: bool = False,
) -> list[dict[str, Any]]:
    """Attach aligned dimensions to groups. P0 default: fill only, keep Layer-1 order."""
    if not groups or not _in_scope_items(draft):
        return groups[: max(1, top_k)]

    enriched_list: list[dict[str, Any]] = []
    for group in groups:
        meta = dict(group.get("metadata") or {})
        engagement_id = group.get("engagement_id") or meta.get("engagement_id")
        source_doc = group.get("source_doc") or meta.get("source_doc")
        try:
            chunks = list(fetch_chunks(engagement_id, source_doc) or [])
        except Exception:
            chunks = list(group.get("hits") or [])
        if not chunks:
            chunks = list(group.get("hits") or [])

        aligned = align_sections_for_engagement(draft, chunks)
        enriched = dict(group)
        enriched["section_coverage"] = aligned["section_coverage"]
        enriched["section_content_mean"] = aligned["section_content_mean"]
        enriched["aligned_dimensions"] = aligned["dimensions"]
        enriched_list.append(enriched)

    if rerank:
        enriched_list.sort(
            key=lambda g: (
                float(g.get("section_coverage") or 0.0),
                float(g.get("similarity_score") or 0.0),
            ),
            reverse=True,
        )
    return enriched_list[: max(1, top_k)]


_SAME_SOURCE_VALUE = "同源 RFQ（与当前上传文件内容一致）"


def apply_same_source_layer2_shortcircuit(
    groups: list[dict[str, Any]],
    draft: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """For byte-identical RFQ hits: full coverage + match=True; keep soft excerpts when present.

    Different-source groups are returned unchanged.
    """
    items = _in_scope_items(draft)
    if not groups or not items:
        return groups

    out: list[dict[str, Any]] = []
    for group in groups:
        meta = dict(group.get("metadata") or {})
        is_same = bool(group.get("same_source") or meta.get("same_source"))
        if not is_same:
            out.append(group)
            continue

        prior = group.get("aligned_dimensions")
        if not isinstance(prior, dict):
            prior = {}
        dimensions: dict[str, dict[str, Any]] = {}
        for item in items:
            name = str(item.get("name") or "")
            if not name:
                continue
            prev = prior.get(name) if isinstance(prior.get(name), dict) else {}
            value = prev.get("value")
            if not value or value == "未知":
                value = _SAME_SOURCE_VALUE
            dimensions[name] = {
                "value": value,
                "match": True,
                "section_path": prev.get("section_path"),
                "chunk_id": prev.get("chunk_id"),
                "content_score": 1.0,
                "same_source": True,
            }

        enriched = dict(group)
        enriched["same_source"] = True
        enriched["aligned_dimensions"] = dimensions
        enriched["section_coverage"] = 1.0
        enriched["section_content_mean"] = 1.0
        meta["same_source"] = True
        enriched["metadata"] = meta
        out.append(enriched)
    return out
