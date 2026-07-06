"""Unit tests for R1 knowledge index service."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.config import Settings
from app.services.knowledge_index_service import KnowledgeIndexService, flatten_preview_chunks


def test_flatten_preview_chunks_synthetic():
    report = {
        "corpus_path": "/tmp",
        "rfq": {
            "path": "RFQ.docx",
            "chunks": [
                {
                    "chunk_id": "c1",
                    "chunk_type": "chapter",
                    "chunk_chapter": "3.1",
                    "content": "hello scope",
                    "metadata": {"doc_type": "rfq"},
                }
            ],
        },
    }
    chunks = flatten_preview_chunks(report)
    assert len(chunks) == 1
    assert chunks[0]["metadata"]["locator"]["chapter"] == "3.1"


def test_index_chunks_mock_embed_and_store(monkeypatch, tmp_path):
    settings = Settings(mock_rag=False, chroma_path=str(tmp_path / "chroma"))
    svc = KnowledgeIndexService(settings, namespace="test_ns")

    class FakeStore:
        def __init__(self, namespace: str):
            self.rows: dict[str, dict] = {}
            self.namespace = namespace

        def is_available(self):
            return True

        def clear_namespace(self, namespace=None):
            self.rows.clear()
            return 0

        def upsert_batch(self, **kwargs):
            for cid, content, meta in zip(
                kwargs["chunk_ids"], kwargs["contents"], kwargs["metadatas"], strict=False
            ):
                self.rows[cid] = {"content": content, "metadata": meta}
            return len(kwargs["chunk_ids"])

        def count(self, namespace=None):
            return len(self.rows)

        def search_by_embedding(self, query_embedding, top_k=5, namespace=None):
            return [
                {
                    "chunk_id": "c1",
                    "content": "hello",
                    "metadata": {"doc_type": "rfq", "chunk_id": "c1"},
                    "similarity_score": 0.88,
                }
            ]

        def get_by_id(self, chunk_id):
            row = self.rows.get(chunk_id)
            if not row:
                return None
            return {"chunk_id": chunk_id, **row}

    fake = FakeStore("test_ns")
    monkeypatch.setattr(svc, "_store", fake)
    monkeypatch.setattr(
        "app.services.knowledge_index_service.embed_texts",
        lambda s, texts: [[0.01] * 768 for _ in texts],
    )
    monkeypatch.setattr("app.services.knowledge_index_service.PgVectorStore.ensure_schema", lambda: None)

    chunks = [
        {
            "chunk_id": "c1",
            "content": "hello",
            "chunk_type": "chapter",
            "chunk_chapter": "3.1",
            "metadata": {"doc_type": "rfq", "chunk_id": "c1"},
        }
    ]
    result = svc.index_chunks(chunks, corpus_path="/tmp/corpus")
    assert result["chunk_count"] == 1
    assert result["vector_store"] == "pgvector"

    hits = svc.search("hello", top_k=3)
    assert len(hits) == 1
    assert hits[0]["similarity_score"] == 0.88
