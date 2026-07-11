"""Shared retrieval eval logic (R1-K09 · production + debug)."""

from __future__ import annotations

from typing import Any, Callable


SearchFn = Callable[[str, list[str] | None], list[dict[str, Any]]]


def evaluate_retrieval_queries(
    search: SearchFn,
    queries: list[dict[str, Any]],
    *,
    top_k: int = 3,
) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    passed = 0
    for idx, item in enumerate(queries):
        q = str(item.get("query") or "").strip()
        if len(q) < 2:
            continue
        doc_types = item.get("expected_doc_types")
        filter_types = list(doc_types) if doc_types else None
        hits = search(q, filter_types)
        ok = _query_passes(item, hits)
        if ok:
            passed += 1
        results.append(
            {
                "index": idx,
                "query": q,
                "expected_source_doc": item.get("expected_source_doc"),
                "expected_area": item.get("expected_area"),
                "expected_doc_types": doc_types,
                "pass": ok,
                "top_hit": hits[0] if hits else None,
                "hits": hits,
            }
        )
    total = len(results)
    return {
        "total": total,
        "passed": passed,
        "pass_rate": round(passed / total, 4) if total else 0.0,
        "results": results,
    }


def _query_passes(item: dict[str, Any], hits: list[dict[str, Any]]) -> bool:
    if not hits:
        return False
    top = hits[0]
    meta = top.get("metadata") or {}
    expected_doc = item.get("expected_source_doc")
    expected_area = item.get("expected_area")
    if expected_doc and expected_doc in str(meta.get("source_doc", "")):
        return True
    if expected_area and expected_area in str(meta.get("area", "")):
        return True
    if not expected_doc and not expected_area:
        return float(top.get("similarity_score") or 0) >= float(item.get("min_score", 0.3))
    return False
