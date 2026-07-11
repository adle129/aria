"""DEV spike: compare vector-only vs hybrid-lite vs hybrid+rerank-lite retrieval."""

from __future__ import annotations

import json
import re
from typing import Any, Literal

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import Settings
from app.database import engine
from app.services.embedding_service import embed_texts
from app.services.knowledge_index_service import VALIDATION_NAMESPACE, KnowledgeIndexService
from app.services.pgvector_store import PgVectorStore

SearchMode = Literal["vector", "hybrid_lite", "hybrid_rerank_lite"]
RRF_K = 60


def tokenize_query(query: str) -> list[str]:
    """Split query into terms (EN words + CN segments) for keyword spike."""
    q = query.strip().lower()
    if not q:
        return []
    parts = re.findall(r"[a-z0-9]{2,}|[\u4e00-\u9fff]{2,}", q)
    seen: set[str] = set()
    out: list[str] = []
    for p in parts:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def _hit_text_blob(hit: dict[str, Any]) -> str:
    meta = hit.get("metadata") or {}
    bits = [
        hit.get("content") or "",
        meta.get("source_doc") or "",
        meta.get("chunk_chapter") or "",
        meta.get("area") or "",
        meta.get("project_name") or "",
    ]
    return " ".join(str(b) for b in bits).lower()


def keyword_overlap_score(query: str, hit: dict[str, Any]) -> float:
    terms = tokenize_query(query)
    if not terms:
        return 0.0
    blob = _hit_text_blob(hit)
    hits = sum(1 for t in terms if t in blob)
    return hits / len(terms)


def reciprocal_rank_fusion(rank_lists: list[list[str]], *, k: int = RRF_K) -> dict[str, float]:
    scores: dict[str, float] = {}
    for ranked_ids in rank_lists:
        for rank, chunk_id in enumerate(ranked_ids, start=1):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank)
    return scores


def rerank_lite(query: str, hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Spike rerank: 0.6 vector similarity + 0.4 keyword overlap (no cross-encoder)."""
    if not hits:
        return []
    scored: list[tuple[float, dict[str, Any]]] = []
    for hit in hits:
        vec = float(hit.get("similarity_score") or 0.0)
        kw = keyword_overlap_score(query, hit)
        combined = 0.6 * vec + 0.4 * kw
        row = dict(hit)
        row["rerank_score"] = round(combined, 4)
        scored.append((combined, row))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [row for _, row in scored]


def _list_namespace_chunks(namespace: str) -> list[dict[str, Any]]:
    sql = text(
        """
        SELECT chunk_id, content, metadata
        FROM knowledge_chunks
        WHERE namespace = :ns
        """
    )
    with Session(engine) as session:
        rows = session.execute(sql, {"ns": namespace}).mappings().all()
    hits: list[dict[str, Any]] = []
    for row in rows:
        meta = row["metadata"]
        if isinstance(meta, str):
            meta = json.loads(meta)
        hits.append(
            {
                "chunk_id": row["chunk_id"],
                "content": row["content"],
                "metadata": dict(meta or {}),
            }
        )
    return hits


def _keyword_search(
    query: str,
    *,
    namespace: str = VALIDATION_NAMESPACE,
    top_k: int = 20,
) -> list[dict[str, Any]]:
    terms = tokenize_query(query)
    if not terms:
        return []
    scored: list[tuple[float, dict[str, Any]]] = []
    for row in _list_namespace_chunks(namespace):
        kw = keyword_overlap_score(query, row)
        if kw <= 0:
            continue
        hit = dict(row)
        hit["keyword_score"] = round(kw, 4)
        hit["similarity_score"] = round(kw, 4)
        scored.append((kw, hit))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [h for _, h in scored[:top_k]]


def _vector_search(
    settings: Settings,
    query: str,
    *,
    top_k: int,
    function_filter: list[str] | None = None,
    doc_type_filter: list[str] | None = None,
) -> list[dict[str, Any]]:
    index = KnowledgeIndexService(settings, namespace=VALIDATION_NAMESPACE)
    return index.search(
        query,
        top_k=top_k,
        function_filter=function_filter,
        doc_type_filter=doc_type_filter,
    )


def _vector_recall(
    settings: Settings,
    query: str,
    *,
    recall_k: int,
    namespace: str = VALIDATION_NAMESPACE,
) -> list[dict[str, Any]]:
    store = PgVectorStore(namespace=namespace)
    if store.count() == 0:
        return []
    query_vec = embed_texts(settings, [query])[0]
    return store.search_by_embedding(query_vec, top_k=recall_k)


def search_hybrid_lite(
    settings: Settings,
    query: str,
    *,
    top_k: int = 5,
    recall_k: int = 20,
    doc_type_filter: list[str] | None = None,
) -> list[dict[str, Any]]:
    from app.services.rag_service import _filter_hits_by_doc_type

    vec_hits = _vector_recall(settings, query, recall_k=recall_k)
    kw_hits = _keyword_search(query, top_k=recall_k)
    by_id: dict[str, dict[str, Any]] = {}
    for hit in vec_hits + kw_hits:
        by_id[hit["chunk_id"]] = hit
    rrf = reciprocal_rank_fusion(
        [[h["chunk_id"] for h in vec_hits], [h["chunk_id"] for h in kw_hits]]
    )
    merged: list[dict[str, Any]] = []
    for cid, rrf_score in sorted(rrf.items(), key=lambda x: x[1], reverse=True):
        row = dict(by_id[cid])
        row["rrf_score"] = round(rrf_score, 5)
        row["similarity_score"] = round(rrf_score, 4)
        merged.append(row)
    merged = _filter_hits_by_doc_type(merged, doc_type_filter)
    return merged[:top_k]


def search_by_mode(
    settings: Settings,
    query: str,
    mode: SearchMode,
    *,
    top_k: int = 3,
    recall_k: int = 20,
    function_filter: list[str] | None = None,
    doc_type_filter: list[str] | None = None,
) -> list[dict[str, Any]]:
    if mode == "vector":
        return _vector_search(
            settings,
            query,
            top_k=top_k,
            function_filter=function_filter,
            doc_type_filter=doc_type_filter,
        )
    if mode == "hybrid_lite":
        return search_hybrid_lite(
            settings,
            query,
            top_k=top_k,
            recall_k=recall_k,
            doc_type_filter=doc_type_filter,
        )
    # hybrid_rerank_lite
    pool = search_hybrid_lite(
        settings,
        query,
        top_k=max(recall_k, top_k * 3),
        recall_k=recall_k,
        doc_type_filter=doc_type_filter,
    )
    reranked = rerank_lite(query, pool)
    return reranked[:top_k]


def eval_hit(item: dict[str, Any], hits: list[dict[str, Any]]) -> bool:
    expected_doc = item.get("expected_source_doc")
    expected_area = item.get("expected_area")
    if not hits:
        return False
    top = hits[0]
    meta = top.get("metadata") or {}
    if expected_doc and expected_doc in str(meta.get("source_doc", "")):
        return True
    if expected_area and expected_area in str(meta.get("area", "")):
        return True
    if not expected_doc and not expected_area:
        score = float(top.get("rerank_score") or top.get("similarity_score") or 0.0)
        return score >= float(item.get("min_score", 0.3))
    return False


def _summarize_top_hits(hits: list[dict[str, Any]], limit: int = 3) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for hit in hits[:limit]:
        meta = hit.get("metadata") or {}
        rows.append(
            {
                "chunk_id": hit.get("chunk_id"),
                "score": hit.get("rerank_score") or hit.get("similarity_score"),
                "doc_type": meta.get("doc_type"),
                "chapter": meta.get("chunk_chapter") or meta.get("area"),
                "source_doc": meta.get("source_doc"),
                "preview": (hit.get("content") or "")[:160],
            }
        )
    return rows


def compare_retrieval_modes(
    settings: Settings,
    queries: list[dict[str, Any]],
    *,
    top_k: int = 3,
    recall_k: int = 20,
    modes: tuple[SearchMode, ...] = ("vector", "hybrid_lite", "hybrid_rerank_lite"),
) -> dict[str, Any]:
    mode_stats = {m: {"passed": 0, "total": 0} for m in modes}
    query_rows: list[dict[str, Any]] = []

    for item in queries:
        q = str(item.get("query") or "").strip()
        if len(q) < 2:
            continue
        row: dict[str, Any] = {
            "query": q,
            "expected_doc_types": item.get("expected_doc_types"),
            "expected_source_doc": item.get("expected_source_doc"),
            "expected_area": item.get("expected_area"),
            "modes": {},
        }
        for mode in modes:
            hits = search_by_mode(
                settings,
                q,
                mode,
                top_k=top_k,
                recall_k=recall_k,
                doc_type_filter=item.get("expected_doc_types"),
            )
            ok = eval_hit(item, hits)
            mode_stats[mode]["total"] += 1
            if ok:
                mode_stats[mode]["passed"] += 1
            row["modes"][mode] = {
                "pass": ok,
                "top_hits": _summarize_top_hits(hits, top_k),
            }
        query_rows.append(row)

    summary = {}
    for mode in modes:
        total = mode_stats[mode]["total"]
        passed = mode_stats[mode]["passed"]
        summary[mode] = {
            "passed": passed,
            "total": total,
            "pass_rate": round(passed / total, 2) if total else 0.0,
        }
    return {
        "modes": list(modes),
        "top_k": top_k,
        "recall_k": recall_k,
        "summary": summary,
        "queries": query_rows,
    }
