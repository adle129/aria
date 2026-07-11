#!/usr/bin/env python3
"""Index validation corpus (Ollama embedding) and run sample RAG queries — DEV validation."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

DEFAULT_CORPUS = Path(r"E:/AI文档项目/RE_ 报价AI需求沟通")


def main() -> int:
    parser = argparse.ArgumentParser(description="KB debug: index corpus + sample search")
    parser.add_argument("--corpus", default=os.environ.get("ARIA_VALIDATION_CORPUS", str(DEFAULT_CORPUS)))
    parser.add_argument("--query", action="append", dest="queries", help="Search query (repeatable)")
    parser.add_argument("--skip-index", action="store_true", help="Only search existing index")
    parser.add_argument("--eval", action="store_true", help="Run built-in eval queries")
    args = parser.parse_args()

    os.environ.setdefault("ARIA_UI_PROFILE", "dev")
    os.environ.setdefault("KB_DEBUG_ENABLED", "true")
    os.environ.setdefault("MOCK_RAG", "false")

    from app.config import get_settings
    from app.services.embedding_service import EmbeddingError
    from app.services.kb_debug_service import KBDebugService
    from app.services.pgvector_store import PgVectorStore

    get_settings.cache_clear()
    settings = get_settings()
    if not settings.kb_debug_enabled:
        print("ERROR: KB_DEBUG_ENABLED requires ARIA_UI_PROFILE=dev", file=sys.stderr)
        return 1

    svc = KBDebugService(settings)
    status = svc.get_status()
    print(json.dumps({"status": status}, ensure_ascii=False, indent=2))

    if not status.get("embedding_model_ready"):
        print("\nERROR: Ollama embedding model not ready. Run: ollama pull nomic-embed-text", file=sys.stderr)
        return 2
    if not PgVectorStore.is_available():
        print(
            "\nERROR: pgvector requires PostgreSQL. Start: docker compose up -d postgres",
            file=sys.stderr,
        )
        return 2

    corpus = Path(args.corpus)
    if not args.skip_index:
        try:
            result = svc.index_corpus(corpus)
            print("\n=== Indexed ===")
            print(json.dumps(result, ensure_ascii=False, indent=2))
        except (EmbeddingError, FileNotFoundError, ValueError) as exc:
            print(f"\nERROR: index failed: {exc}", file=sys.stderr)
            return 3

    if args.eval:
        sample_path = ROOT / "backend" / "data" / "debug_eval_queries.sample.json"
        eval_queries = json.loads(sample_path.read_text(encoding="utf-8"))
        report = svc.run_eval(eval_queries, top_k=3)
        print("\n=== Eval ===")
        print(json.dumps({"total": report["total"], "passed": report["passed"], "pass_rate": report["pass_rate"]}, indent=2))
        for row in report["results"]:
            mark = "PASS" if row["pass"] else "FAIL"
            print(f"  [{mark}] {row['query']}")

    queries = args.queries or []
    if not queries and not args.eval:
        queries = ["物理对标 benchmark", "项目总体要求 整车工程", "通用公差 mounting"]

    for q in queries:
        qtext = q if isinstance(q, str) else str(q)
        print(f"\n=== Search: {qtext} ===")
        try:
            hits = svc.search(qtext, top_k=3)
        except EmbeddingError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 4
        for i, hit in enumerate(hits, 1):
            meta = hit.get("metadata") or {}
            print(
                f"  {i}. score={hit.get('similarity_score')} "
                f"type={meta.get('doc_type')} chapter={meta.get('chunk_chapter') or meta.get('area')}"
            )
            print(f"     {str(hit.get('content', ''))[:120]}…")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
