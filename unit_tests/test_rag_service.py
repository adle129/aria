import pytest

from app.config import Settings
from app.services.rag_service import RAGProductionError, RAGService, compute_function_coverage


def test_knowledge_and_rfq_share_same_search_pipeline():
    """RFQ 对标与 POST /knowledge/search 共用 search_similar_projects（同源契约）。"""
    rag = RAGService(Settings(mock_rag=True, knowledge_base_path="./data/knowledge_base"))
    query = "MEB chassis suspension"
    rfq_hits = rag.search_similar_projects(query, top_k=3)
    kb_hits = rag.search_similar_projects(query, top_k=3)
    assert rfq_hits == kb_hits
    assert rfq_hits[0]["metadata"]["source_doc"] == kb_hits[0]["metadata"]["source_doc"]


def test_mock_search_returns_top_k():
    rag = RAGService(Settings(mock_rag=True, knowledge_base_path="./data/knowledge_base"))
    results = rag.search_similar_projects("MEB chassis", top_k=2)
    assert len(results) == 2
    assert results[0]["similarity_score"] >= results[1]["similarity_score"]


def test_mock_search_hit_schema():
    rag = RAGService(Settings(mock_rag=True, knowledge_base_path="./data/knowledge_base"))
    hit = rag.search_similar_projects("chassis", top_k=1)[0]
    assert "content" in hit
    assert "similarity_score" in hit
    meta = hit["metadata"]
    assert "project_name" in meta
    assert "source_doc" in meta
    assert "functions" in meta


def test_search_function_filter():
    rag = RAGService(Settings(mock_rag=True, knowledge_base_path="./data/knowledge_base"))
    results = rag.search_similar_projects("chassis", top_k=5, function_filter=["PM"])
    assert all("PM" in (h.get("metadata") or {}).get("functions", []) for h in results)


def test_compute_function_coverage_uncovered():
    hits = [
        {"metadata": {"functions": ["PM", "Chassis"]}},
        {"metadata": {"functions": ["Chassis"]}},
    ]
    coverage = compute_function_coverage(["PM", "Chassis", "BIW"], hits)
    assert coverage["uncovered"] == ["BIW"]
    assert "PM" in coverage["covered"]
    assert "Chassis" in coverage["covered"]


def test_build_comparison_table_has_confidence_and_coverage():
    rag = RAGService(Settings(mock_rag=True, knowledge_base_path="./data/knowledge_base"))
    rfq_data = {"project_name": "test", "functions_in_scope": ["PM", "Chassis", "BIW"]}
    docs = rag.search_similar_projects("chassis", top_k=3)
    table = rag.build_comparison_table(rfq_data, docs)
    assert table["overall_confidence"] in {"高", "中", "低"}
    assert len(table["projects"]) >= 1
    assert "matrix_rows" in table
    assert len(table["matrix_rows"]) >= 5
    assert "function_coverage" in table
    assert "BIW" in table["function_coverage"]["uncovered"]
    assert table["insufficient_evidence"] is False


def test_build_comparison_table_propagates_engagement_id():
    rag = RAGService(Settings(mock_rag=True, knowledge_base_path="./data/knowledge_base"))
    rfq_data = {"project_name": "test", "functions_in_scope": ["PM", "Chassis"]}
    docs = rag.search_similar_projects("chassis", top_k=1)
    table = rag.build_comparison_table(rfq_data, docs)
    assert table["projects"][0]["engagement_id"] == "mock_project_1"


def test_insufficient_evidence_when_empty_or_low_score():
    rag = RAGService(
        Settings(mock_rag=False, rag_similarity_threshold=0.65, knowledge_base_path="./data/knowledge_base")
    )
    assert rag.is_insufficient_evidence([]) is True
    assert rag.is_insufficient_evidence([{"similarity_score": 0.5}]) is True
    assert rag.is_insufficient_evidence([{"similarity_score": 0.8}]) is False


def test_build_comparison_table_insufficient_evidence_no_mock_projects():
    rag = RAGService(
        Settings(mock_rag=False, rag_similarity_threshold=0.65, knowledge_base_path="./data/knowledge_base")
    )
    rfq_data = {"project_name": "test", "functions_in_scope": ["PM"]}
    table = rag.build_comparison_table(rfq_data, [])
    assert table["insufficient_evidence"] is True
    assert table["projects"] == []
    assert "暂无足够历史项目" in table["recommendation"]


def test_search_doc_type_filter():
    rag = RAGService(Settings(mock_rag=True, knowledge_base_path="./data/knowledge_base"))
    results = rag.search_similar_projects("chassis", top_k=5, doc_type_filter=["summary"])
    assert all((h.get("metadata") or {}).get("doc_type") == "summary" for h in results)


def test_search_delegates_to_knowledge_index_service(monkeypatch, tmp_path):
    """SPK-K03: production RAG uses KnowledgeIndexService.search with same filters."""
    kb = tmp_path / "kb"
    kb.mkdir()
    rag = RAGService(
        Settings(
            mock_rag=False,
            knowledge_base_path=str(kb),
            knowledge_vector_namespace="production",
        )
    )
    calls: list[tuple] = []

    class FakeIndex:
        namespace = "production"

        def search(
            self,
            query: str,
            *,
            top_k: int = 5,
            function_filter: list[str] | None = None,
            doc_type_filter: list[str] | None = None,
            request_type: str = "query",
        ):
            calls.append((query, top_k, function_filter, doc_type_filter, request_type))
            return [
                {
                    "content": "scope text",
                    "similarity_score": 0.91,
                    "metadata": {
                        "doc_type": "rfq",
                        "project_name": "Demo",
                        "source_doc": "knowledge_base/eng/rfq.docx",
                        "functions": ["Chassis"],
                    },
                }
            ]

    monkeypatch.setattr(
        "app.services.knowledge_index_service.KnowledgeIndexService",
        lambda _settings, namespace=None: FakeIndex(),
    )
    hits = rag.search_similar_projects(
        "MEB chassis",
        top_k=3,
        function_filter=["Chassis"],
        doc_type_filter=["rfq"],
    )
    assert len(calls) == 1
    assert calls[0] == ("MEB chassis", 3, ["Chassis"], ["rfq"], "query")
    assert hits[0]["similarity_score"] == 0.91
    assert hits[0]["metadata"]["doc_type"] == "rfq"


def test_real_search_empty_returns_no_mock_fallback(monkeypatch, tmp_path):
    kb = tmp_path / "kb"
    kb.mkdir()
    chroma = tmp_path / "chroma"
    rag = RAGService(
        Settings(mock_rag=False, knowledge_base_path=str(kb), chroma_path=str(chroma))
    )

    class FakeIndex:
        def search(
            self,
            query: str,
            top_k: int = 5,
            function_filter: list[str] | None = None,
            doc_type_filter: list[str] | None = None,
            request_type: str = "query",
        ):
            return []

    monkeypatch.setattr(
        "app.services.knowledge_index_service.KnowledgeIndexService",
        lambda _settings, namespace=None: FakeIndex(),
    )
    assert rag.search_similar_projects("MEB chassis", top_k=3) == []


def test_list_documents_mock():
    rag = RAGService(Settings(mock_rag=True, knowledge_base_path="./data/knowledge_base"))
    docs = rag.list_documents()
    assert len(docs) == 3
    statuses = {d["status"] for d in docs}
    assert statuses == {"indexed", "pending", "failed"}


def test_import_skips_unchanged_hash(tmp_path):
    kb = tmp_path / "kb" / "proj_a"
    kb.mkdir(parents=True)
    doc = kb / "rfq.docx"
    doc.write_bytes(b"fake docx content for hash test")

    rag = RAGService(
        Settings(mock_rag=True, knowledge_base_path=str(tmp_path / "kb"))
    )
    first = rag.import_documents()
    assert first["new_documents"] == 1
    assert first["skipped"] == 0

    second = rag.import_documents()
    assert second["new_documents"] == 1
    assert second["new_chunks"] == 10


def test_import_documents_production_raises():
    rag = RAGService(
        Settings(mock_rag=False, knowledge_base_path="./data/knowledge_base")
    )
    with pytest.raises(RAGProductionError, match="reindex"):
        rag.import_documents()


def test_get_stats_production_uses_pgvector(monkeypatch, tmp_path):
    kb = tmp_path / "kb"
    kb.mkdir()
    rag = RAGService(
        Settings(mock_rag=False, knowledge_base_path=str(kb), knowledge_vector_namespace="prod")
    )

    class FakeIndex:
        namespace = "prod"

        def indexed_count(self):
            return 42

        def last_index_state(self):
            return {"last_index_at": "2026-01-01T00:00:00Z", "embedding_model": "nomic-embed-text"}

        def list_indexed_source_docs(self):
            return set()

    monkeypatch.setattr(rag, "_index_service", lambda: FakeIndex())
    stats = rag.get_stats()
    assert stats["vector_store"] == "pgvector"
    assert stats["total_chunks"] == 42
    assert stats["mock_rag"] is False


def test_list_documents_production_from_manifest(tmp_path, monkeypatch):
    kb = tmp_path / "kb" / "eng_001"
    kb.mkdir(parents=True)
    (kb / "rfq.docx").write_bytes(b"rfq")
    (kb / "manifest.json").write_text(
        '{"engagement_id":"eng_001","project_name":"Demo Project","documents":[{"path":"rfq.docx","doc_type":"rfq"}]}',
        encoding="utf-8",
    )

    rag = RAGService(Settings(mock_rag=False, knowledge_base_path=str(tmp_path / "kb")))

    class FakeIndex:
        def list_indexed_source_docs(self):
            return {"knowledge_base/eng_001/rfq.docx"}

    monkeypatch.setattr(rag, "_index_service", lambda: FakeIndex())
    docs = rag.list_documents()
    assert len(docs) == 1
    assert docs[0]["status"] == "indexed"
    assert docs[0]["engagement_id"] == "eng_001"
    assert docs[0]["doc_type"] == "rfq"


def test_mock_stats_includes_function_coverage():
    rag = RAGService(Settings(mock_rag=True, knowledge_base_path="./data/knowledge_base"))
    stats = rag.get_stats()
    assert stats["total_documents"] > 0
    assert "function_coverage" in stats
    assert stats["function_coverage"]["Chassis"] >= 0.9
