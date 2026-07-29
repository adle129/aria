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


def _normalize_keyword_list(raw: Any) -> list[str]:
    if not isinstance(raw, (list, tuple)):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for item in raw:
        text = str(item or "").strip()
        if not text:
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(text)
    return out


def resolve_align_keywords(
    item: dict[str, Any] | None,
    *,
    keyword_index: dict[str, list[str]] | None = None,
) -> list[str]:
    """Prefer draft-item keywords; else baseline index by dimension_id / name."""
    if isinstance(item, dict):
        from_item = _normalize_keyword_list(item.get("keywords"))
        if from_item:
            return from_item
        if keyword_index:
            dim_id = str(item.get("dimension_id") or item.get("id") or "").strip()
            name = str(item.get("name") or "").strip()
            if dim_id and dim_id in keyword_index:
                return list(keyword_index[dim_id])
            if name and name in keyword_index:
                return list(keyword_index[name])
    return []


def load_baseline_keyword_index() -> dict[str, list[str]]:
    """Best-effort load from configured dimension baseline JSON (no hard-coded terms)."""
    try:
        from app.config import get_settings
        from app.services.dimension_baseline_service import (
            DimensionBaselineNotFoundError,
            DimensionBaselineService,
        )

        return DimensionBaselineService(get_settings()).keyword_index()
    except (DimensionBaselineNotFoundError, ValueError, OSError):
        return {}
    except Exception:  # noqa: BLE001 — align must not fail if baseline missing
        return {}


def title_overlap_score_with_keywords(
    dim_name: Any,
    title_blob: Any,
    keywords: list[str] | None = None,
) -> tuple[float, str | None]:
    """Best title overlap using dimension name or any configured keyword/alias."""
    best = title_overlap_score(dim_name, title_blob)
    matched_via: str | None = "name" if best > 0 else None
    for kw in keywords or []:
        score = title_overlap_score(kw, title_blob)
        if score > best:
            best = score
            matched_via = "keyword"
    return best, matched_via if best > 0 else None


def _in_scope_items(draft: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(draft, dict):
        return []
    rows = list(draft.get("items") or []) + list(draft.get("custom_items") or [])
    return [
        item
        for item in rows
        if isinstance(item, dict) and item.get("in_scope") is True and item.get("name")
    ]


def _body_term_hits(
    dim_name: str,
    work_content: str,
    chunks: list[dict[str, Any]],
    *,
    keywords: list[str] | None = None,
) -> int:
    """Count chunks whose body contains any token from name / work_content / keywords."""
    tokens = _title_tokens(dim_name) | _title_tokens(work_content)
    for kw in keywords or []:
        tokens |= _title_tokens(kw)
    if not tokens:
        return 0
    hits = 0
    for chunk in chunks:
        body = _content_body(chunk)
        if not body:
            continue
        blob = _WS_RE.sub(" ", body.strip().casefold())
        if any(tok in blob for tok in tokens):
            hits += 1
    return hits


def diagnose_align_miss(
    dim_name: str,
    work_content: str,
    chunks: list[dict[str, Any]],
    *,
    title_min: float = TITLE_ALIGN_MIN,
    status: str = "title_below_threshold",
    keywords: list[str] | None = None,
) -> dict[str, Any]:
    """
    Explain why Layer-2 title align failed for a dimension.

    Rule-based (section_path vs dimension name + baseline keywords), not LLM generation.
    """
    if not chunks:
        return {
            "status": "no_chunks",
            "reason_code": "EMPTY_DOC",
            "reason_zh": "历史文档无可用分块（可能未切到章节或解析失败）",
            "title_min": title_min,
            "chunk_count": 0,
            "best_title_score": 0.0,
            "best_section_path": None,
            "body_term_hits": 0,
            "keywords_used": list(keywords or []),
        }

    best_score = 0.0
    best_path: str | None = None
    for chunk in chunks:
        score, _via = title_overlap_score_with_keywords(
            dim_name, _chunk_title_blob(chunk), keywords
        )
        if score >= best_score:
            best_score = score
            meta = chunk.get("metadata") or {}
            best_path = meta.get("section_path") or None

    body_hits = _body_term_hits(dim_name, work_content, chunks, keywords=keywords)
    if status == "empty_body":
        reason_code = "EMPTY_CHUNK_BODY"
        reason_zh = "章节标题已过门槛，但对应分块正文为空"
    elif body_hits > 0:
        reason_code = "TITLE_MISMATCH"
        reason_zh = (
            f"正文里能找到维度相关词（{body_hits} 个分块），"
            f"但章节标题与基线维度名重叠不足"
            f"（最高 {best_score:.2f} < 门槛 {title_min:.2f}"
            f"{f'，最接近「{best_path}」' if best_path else ''}）。"
            "更可能是标题对齐规则/命名差异，而非文档完全没有内容。"
        )
    else:
        reason_code = "NO_BODY_EVIDENCE"
        reason_zh = (
            f"章节标题未过门槛（最高 {best_score:.2f} < {title_min:.2f}"
            f"{f'，最接近「{best_path}」' if best_path else ''}），"
            "且正文也未出现维度名/工作内容关键词。"
            "更可能是历史 RFQ 无对应主题，或用词与基线维度完全不同。"
        )

    return {
        "status": status,
        "reason_code": reason_code,
        "reason_zh": reason_zh,
        "title_min": title_min,
        "chunk_count": len(chunks),
        "best_title_score": round(float(best_score), 3),
        "best_section_path": best_path,
        "body_term_hits": body_hits,
        "dim_name": dim_name,
        "keywords_used": list(keywords or []),
    }


def align_dimension_to_chunks(
    dim_name: str,
    work_content: str,
    chunks: list[dict[str, Any]],
    *,
    title_min: float = TITLE_ALIGN_MIN,
    value_max_chars: int = VALUE_MAX_CHARS,
    keywords: list[str] | None = None,
) -> dict[str, Any]:
    kws = _normalize_keyword_list(keywords)

    def _unknown(status: str) -> dict[str, Any]:
        return {
            "value": "未知",
            "match": None,
            "section_path": None,
            "chunk_id": None,
            "content_score": 0.0,
            "align_status": status,
            "align_diag": diagnose_align_miss(
                dim_name,
                work_content,
                chunks,
                title_min=title_min,
                status=status,
                keywords=kws,
            ),
        }

    if not chunks:
        return _unknown("no_chunks")

    scored: list[tuple[float, float, str | None, dict[str, Any]]] = []
    for chunk in chunks:
        title_score, matched_via = title_overlap_score_with_keywords(
            dim_name, _chunk_title_blob(chunk), kws
        )
        if title_score < title_min:
            continue
        body = _content_body(chunk)
        content_score = content_overlap_score(work_content, body) if work_content else title_score
        scored.append((title_score, content_score, matched_via, chunk))

    if not scored:
        return _unknown("title_below_threshold")

    scored.sort(key=lambda row: (row[1], row[0]), reverse=True)
    best_title, best_content, matched_via, best = scored[0]
    meta = best.get("metadata") or {}
    body = _content_body(best).strip()
    if not body:
        return _unknown("empty_body")
    value = body if len(body) <= value_max_chars else body[:value_max_chars].rstrip() + "…"

    if best_content >= CONTENT_MATCH_TRUE or (
        best_title >= 0.7 and best_content >= CONTENT_MATCH_FALSE
    ):
        match: bool | None = True
    elif best_content < CONTENT_MATCH_FALSE and best_title < 0.55:
        match = False
    else:
        match = None

    via = matched_via or "name"
    reason_zh = (
        "已按基线关键词对齐到章节正文摘录"
        if via == "keyword"
        else "已按章节标题对齐到正文摘录"
    )
    return {
        "value": value,
        "match": match,
        "section_path": meta.get("section_path") or None,
        "chunk_id": best.get("chunk_id") or meta.get("chunk_id"),
        "content_score": round(float(best_content), 3),
        "align_status": "matched",
        "align_diag": {
            "status": "matched",
            "reason_code": "OK",
            "reason_zh": reason_zh,
            "title_min": title_min,
            "best_title_score": round(float(best_title), 3),
            "best_section_path": meta.get("section_path") or None,
            "body_term_hits": None,
            "dim_name": dim_name,
            "match_via": via,
            "keywords_used": kws,
        },
    }


def align_sections_for_engagement(
    draft: dict[str, Any] | None,
    chunks: list[dict[str, Any]],
    *,
    title_min: float = TITLE_ALIGN_MIN,
    value_max_chars: int = VALUE_MAX_CHARS,
    keyword_index: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    items = _in_scope_items(draft)
    index = keyword_index if keyword_index is not None else load_baseline_keyword_index()
    dimensions: dict[str, dict[str, Any]] = {}
    content_scores: list[float] = []
    aligned = 0

    for item in items:
        name = str(item.get("name") or "")
        work = str(item.get("work_content") or "")
        kws = resolve_align_keywords(item, keyword_index=index)
        cell = align_dimension_to_chunks(
            name,
            work,
            chunks,
            title_min=title_min,
            value_max_chars=value_max_chars,
            keywords=kws,
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
    keyword_index: dict[str, list[str]] | None = None,
) -> list[dict[str, Any]]:
    """Attach aligned dimensions to groups. P0 default: fill only, keep Layer-1 order."""
    if not groups or not _in_scope_items(draft):
        return groups[: max(1, top_k)]

    index = keyword_index if keyword_index is not None else load_baseline_keyword_index()
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

        aligned = align_sections_for_engagement(
            draft, chunks, keyword_index=index
        )
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


# Same-file shortcircuit must not claim "content is identical" in a cell that
# has no excerpt — document-level fingerprint ≠ dimension→chapter alignment.
# Prefer real Layer-2 excerpts; otherwise a neutral "no section matched" note.
_SAME_SOURCE_FALLBACK = "未匹配到对应章节"


def apply_same_source_layer2_shortcircuit(
    groups: list[dict[str, Any]],
    draft: dict[str, Any] | None,
    *,
    fetch_chunks: Any | None = None,
    soft_title_min: float = 0.15,
    keyword_index: dict[str, list[str]] | None = None,
) -> list[dict[str, Any]]:
    """For same-file RFQ hits: full coverage + match=True; prefer real excerpts.

    Keeps Layer-2 chapter excerpts when present. For missing dims, optionally
    retries alignment with a lower title threshold (same-file bodies are rich).
    Never fills the matrix with a 「同源 RFQ…」slogan.
    Different-source groups are returned unchanged.
    """
    items = _in_scope_items(draft)
    if not groups or not items:
        return groups

    index = keyword_index if keyword_index is not None else load_baseline_keyword_index()
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

        chunks: list[dict[str, Any]] | None = None
        if fetch_chunks is not None:
            try:
                chunks = fetch_chunks(
                    group.get("engagement_id") or meta.get("engagement_id"),
                    group.get("source_doc") or meta.get("source_doc"),
                )
            except Exception:  # noqa: BLE001 — best-effort soft refill
                chunks = None

        dimensions: dict[str, dict[str, Any]] = {}
        for item in items:
            name = str(item.get("name") or "")
            if not name:
                continue
            work = str(item.get("work_content") or "")
            kws = resolve_align_keywords(item, keyword_index=index)
            prev = prior.get(name) if isinstance(prior.get(name), dict) else {}
            value = prev.get("value")
            section_path = prev.get("section_path")
            chunk_id = prev.get("chunk_id")
            content_score = prev.get("content_score")

            needs_refill = (not value) or value == "未知" or value == _SAME_SOURCE_FALLBACK
            # Legacy slogan from older builds — treat as empty for refill.
            if isinstance(value, str) and value.startswith("同源 RFQ"):
                needs_refill = True

            align_status = prev.get("align_status")
            align_diag = prev.get("align_diag") if isinstance(prev.get("align_diag"), dict) else None

            if needs_refill and chunks:
                soft = align_dimension_to_chunks(
                    name,
                    work,
                    chunks,
                    title_min=soft_title_min,
                    keywords=kws,
                )
                if soft.get("value") and soft["value"] != "未知":
                    value = soft["value"]
                    section_path = soft.get("section_path")
                    chunk_id = soft.get("chunk_id")
                    content_score = soft.get("content_score")
                    align_status = soft.get("align_status")
                    align_diag = soft.get("align_diag")
                    needs_refill = False
                else:
                    align_status = soft.get("align_status") or "title_below_threshold"
                    align_diag = soft.get("align_diag") or diagnose_align_miss(
                        name,
                        work,
                        chunks,
                        title_min=soft_title_min,
                        keywords=kws,
                    )

            if needs_refill or not value or value == "未知":
                value = _SAME_SOURCE_FALLBACK
                content_score = 1.0
                if not align_diag:
                    align_diag = diagnose_align_miss(
                        name,
                        work,
                        chunks or [],
                        title_min=soft_title_min,
                        keywords=kws,
                    )
                align_status = align_status or align_diag.get("status") or "title_below_threshold"

            dimensions[name] = {
                "value": value,
                "match": True,
                "section_path": section_path,
                "chunk_id": chunk_id,
                "content_score": 1.0 if content_score is None else content_score,
                "same_source": True,
                "align_status": align_status,
                "align_diag": align_diag,
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