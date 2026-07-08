"""Retrieval evaluation helpers (R1-K09 / SPK-K04)."""

from __future__ import annotations

from typing import Any, Callable

from app.config import Settings
from app.services.rag_service import RAGService

SearchFn = Callable[..., list[dict[str, Any]]]
SPIKE_VECTOR_PASS_MIN = 12
SPIKE_VECTOR_PASS_TOTAL = 15


def eval_retrieval_hit(item: dict[str, Any], hits: list[dict[str, Any]]) -> bool:
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
        score = float(top.get("similarity_score") or 0.0)
        return score >= float(item.get("min_score", 0.3))
    return False


def run_retrieval_eval(
    queries: list[dict[str, Any]],
    search: SearchFn,
    *,
    top_k: int = 3,
) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    passed = 0
    for idx, item in enumerate(queries):
        query = str(item.get("query") or "").strip()
        if len(query) < 2:
            continue
        hits = search(
            query,
            top_k=top_k,
            doc_type_filter=item.get("expected_doc_types"),
        )
        ok = eval_retrieval_hit(item, hits)
        if ok:
            passed += 1
        results.append(
            {
                "index": idx,
                "query": query,
                "expected_source_doc": item.get("expected_source_doc"),
                "expected_area": item.get("expected_area"),
                "pass": ok,
                "top_score": hits[0].get("similarity_score") if hits else None,
            }
        )
    total = len(results)
    return {
        "total": total,
        "passed": passed,
        "pass_rate": round(passed / total, 2) if total else 0.0,
        "results": results,
    }


def run_production_retrieval_eval(
    settings: Settings,
    queries: list[dict[str, Any]],
    *,
    top_k: int = 3,
) -> dict[str, Any]:
    rag = RAGService(settings)

    def _search(
        query: str,
        *,
        top_k: int = 3,
        doc_type_filter: list[str] | None = None,
        function_filter: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        return rag.search_similar_projects(
            query,
            top_k=top_k,
            doc_type_filter=doc_type_filter,
            function_filter=function_filter,
        )

    return run_retrieval_eval(queries, _search, top_k=top_k)
