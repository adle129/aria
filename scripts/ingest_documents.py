#!/usr/bin/env python3
"""Ingest knowledge_base .docx files into ChromaDB (set MOCK_RAG=false)."""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.config import Settings  # noqa: E402
from app.services.rag_service import RAGService  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Import knowledge base documents into ChromaDB")
    parser.add_argument(
        "--knowledge-base",
        default=str(BACKEND / "data" / "knowledge_base"),
        help="Path to knowledge_base directory",
    )
    parser.add_argument(
        "--chroma-path",
        default=str(BACKEND / "data" / "chroma_db"),
        help="ChromaDB persistence directory",
    )
    args = parser.parse_args()

    settings = Settings(
        mock_rag=False,
        knowledge_base_path=args.knowledge_base,
        chroma_path=args.chroma_path,
    )
    rag = RAGService(settings)
    result = rag.import_documents()
    stats = rag.get_stats()
    print(f"Imported documents: {result['new_documents']}")
    print(f"Skipped: {result['skipped']}")
    print(f"Chroma chunks: {result['new_chunks']}")
    print(f"KB stats: {stats['total_documents']} docs, {stats['total_projects']} projects")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
