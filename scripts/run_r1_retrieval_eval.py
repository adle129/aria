#!/usr/bin/env python3
"""Run R1 production-path retrieval eval (15 sample queries · R1-K09 internal gate).

Requires: PostgreSQL + pgvector, MOCK_RAG=false, Ollama nomic-embed-text,
indexed engagements under knowledge_base/ (see seed_internal_engagement.py).

Usage:
  python scripts/seed_internal_engagement.py
  python scripts/ingest_documents.py
  python scripts/run_r1_retrieval_eval.py --min-pass 12
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.embedding_service import EmbeddingError  # noqa: E402

DEFAULT_QUERIES = ROOT / "backend" / "data" / "debug_eval_queries.sample.json"
DEFAULT_REPORT = ROOT / "backend" / "data" / "validation_reports" / "r1_retrieval_eval.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="R1 production retrieval eval")
    parser.add_argument("--queries-file", type=Path, default=DEFAULT_QUERIES)
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--min-pass", type=int, default=12, help="Fail exit if passed < min-pass")
    parser.add_argument("--namespace", default="", help="Override pgvector namespace (default: production)")
    args = parser.parse_args()

    os.environ.setdefault("MOCK_RAG", "false")

    from app.config import get_settings
    from app.services.knowledge_index_service import KnowledgeIndexService
    from app.services.pgvector_store import PgVectorStore
    from app.services.retrieval_eval_service import evaluate_retrieval_queries

    get_settings.cache_clear()
    settings = get_settings()

    if not PgVectorStore.is_available():
        print("ERROR: pgvector requires PostgreSQL (docker compose up -d postgres)", file=sys.stderr)
        return 2

    from app.services.ollama_service import probe_ollama

    probe = probe_ollama(settings.ollama_base_url, settings.ollama_model, settings.embedding_model)
    if not probe.get("embedding_model_ready"):
        print("ERROR: Ollama embedding not ready. Run: ollama pull nomic-embed-text", file=sys.stderr)
        return 2

    namespace = args.namespace or settings.knowledge_vector_namespace
    index = KnowledgeIndexService(settings, namespace=namespace)
    chunk_count = index.indexed_count()
    if chunk_count == 0:
        print(
            "ERROR: no indexed chunks. Run: python scripts/seed_internal_engagement.py && "
            "python scripts/ingest_documents.py",
            file=sys.stderr,
        )
        return 3

    if not args.queries_file.is_file():
        print(f"ERROR: queries file not found: {args.queries_file}", file=sys.stderr)
        return 1

    queries = json.loads(args.queries_file.read_text(encoding="utf-8"))

    def search(q: str, doc_types: list[str] | None) -> list[dict]:
        return index.search(q, top_k=args.top_k, doc_type_filter=doc_types)

    report = evaluate_retrieval_queries(search, queries, top_k=args.top_k)
    report["namespace"] = namespace
    report["indexed_chunks"] = chunk_count
    report["evaluated_at"] = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    report["min_pass"] = args.min_pass
    report["gate_pass"] = report["passed"] >= args.min_pass

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Eval: {report['passed']}/{report['total']} pass ({report['pass_rate']:.0%}) namespace={namespace}")
    for row in report["results"]:
        mark = "PASS" if row["pass"] else "FAIL"
        print(f"  [{mark}] {row['query'][:72]}")
    print(f"Report: {args.output}")

    if not report["gate_pass"]:
        print(f"FAIL: need >= {args.min_pass} passes for internal R1-K09 gate", file=sys.stderr)
        return 4
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except EmbeddingError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(5) from exc
