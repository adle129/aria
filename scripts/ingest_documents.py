#!/usr/bin/env python3
"""Ingest knowledge_base engagements into pgvector (MOCK_RAG=false + PostgreSQL + Ollama)."""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.config import Settings  # noqa: E402
from app.database import engine  # noqa: E402
from app.services.engagement_ingest_service import EngagementIngestService  # noqa: E402
from app.services.rag_service import RAGService  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Re-index knowledge base engagements into pgvector")
    parser.add_argument(
        "--knowledge-base",
        default=str(BACKEND / "data" / "knowledge_base"),
        help="Path to knowledge_base directory",
    )
    args = parser.parse_args()

    settings = Settings(
        mock_rag=False,
        knowledge_base_path=args.knowledge_base,
    )
    session = sessionmaker(bind=engine)()
    try:
        result = EngagementIngestService(settings, session).import_all()
    finally:
        session.close()

    stats = RAGService(settings).get_stats()
    print(f"Indexed chunks: {result.get('new_chunks', 0)}")
    print(f"Engagements indexed: {result.get('engagements_indexed', 0)}")
    print(f"Failed: {len(result.get('failed_files') or [])}")
    print(f"KB stats: {stats['total_documents']} docs, {stats['total_chunks']} chunks, store={stats.get('vector_store')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
