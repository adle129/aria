#!/usr/bin/env python3
"""Spike: compare vector vs hybrid-lite vs hybrid+rerank-lite on the same eval queries.

Prerequisites:
  docker compose up -d postgres
  ollama pull nomic-embed-text
  MOCK_RAG=false

Examples:
  python scripts/spike_rag_compare.py --eval
  python scripts/spike_rag_compare.py --eval --skip-index
  python scripts/spike_rag_compare.py --query "项目总体要求 整车工程"
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

DEFAULT_CORPUS = Path(r"E:/AI文档项目/RE_ 报价AI需求沟通")
DEFAULT_OUT = ROOT / "backend" / "data" / "validation_reports" / "rag_compare_spike.json"
DEFAULT_QUERIES = ROOT / "backend" / "data" / "debug_eval_queries.sample.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="RAG retrieval A/B spike (vector vs hybrid vs rerank-lite)")
    parser.add_argument("--corpus", default=os.environ.get("ARIA_VALIDATION_CORPUS", str(DEFAULT_CORPUS)))
    parser.add_argument("--queries-file", type=Path, default=DEFAULT_QUERIES)
    parser.add_argument("--query", action="append", dest="queries", help="Ad-hoc query (repeatable)")
    parser.add_argument("--eval", action="store_true", help="Run queries from --queries-file")
    parser.add_argument("--skip-index", action="store_true", help="Use existing pgvector index")
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--recall-k", type=int, default=20, help="Recall pool size for hybrid modes")
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    os.environ.setdefault("MOCK_RAG", "false")

    from app.config import get_settings
    from app.services.embedding_service import EmbeddingError
    from app.services.kb_debug_service import KBDebugService
    from app.services.knowledge_index_service import VALIDATION_NAMESPACE, KnowledgeIndexService
    from app.services.pgvector_store import PgVectorStore
    from app.services.rag_spike_service import compare_retrieval_modes

    get_settings.cache_clear()
    settings = get_settings()

    if not PgVectorStore.is_available():
        print("ERROR: pgvector requires PostgreSQL. Start: docker compose up -d postgres", file=sys.stderr)
        return 2

    svc = KBDebugService(settings)
    status = svc.get_status()
    if not status.get("embedding_model_ready"):
        print("ERROR: Ollama embedding not ready. Run: ollama pull nomic-embed-text", file=sys.stderr)
        return 2

    corpus = Path(args.corpus)
    if not args.skip_index:
        print(f"Indexing corpus: {corpus}", flush=True)
        try:
            result = svc.index_corpus(corpus)
            print(f"Indexed {result.get('indexed_chunks', result.get('chunk_count'))} chunks", flush=True)
        except (EmbeddingError, FileNotFoundError, ValueError) as exc:
            print(f"ERROR: index failed: {exc}", file=sys.stderr)
            return 3

    eval_items: list[dict] = []
    if args.eval:
        if not args.queries_file.exists():
            print(f"ERROR: queries file not found: {args.queries_file}", file=sys.stderr)
            return 1
        eval_items = json.loads(args.queries_file.read_text(encoding="utf-8"))

    if args.queries:
        for q in args.queries:
            eval_items.append({"query": q, "min_score": 0.25})

    if not eval_items:
        eval_items = json.loads(DEFAULT_QUERIES.read_text(encoding="utf-8"))

    print(f"Running {len(eval_items)} queries × 3 modes (top_k={args.top_k}, recall_k={args.recall_k})…", flush=True)
    try:
        report = compare_retrieval_modes(
            settings,
            eval_items,
            top_k=args.top_k,
            recall_k=args.recall_k,
        )
    except EmbeddingError as exc:
        print(f"ERROR: search failed: {exc}", file=sys.stderr)
        return 4

    index_svc = KnowledgeIndexService(settings, namespace=VALIDATION_NAMESPACE)
    report["indexed_chunks"] = index_svc.indexed_count()
    report["corpus_path"] = str(corpus)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n=== Summary (Pass rate) ===")
    for mode, stats in report["summary"].items():
        print(f"  {mode:22s} {stats['passed']}/{stats['total']}  ({stats['pass_rate']:.0%})")

    print("\n=== Per query ===")
    for row in report["queries"]:
        marks = " | ".join(
            f"{m}:{'PASS' if row['modes'][m]['pass'] else 'FAIL'}"
            for m in report["modes"]
        )
        print(f"  {row['query'][:50]}")
        print(f"    {marks}")

    print(f"\nReport: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
