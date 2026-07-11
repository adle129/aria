from app.config import Settings
from app.services.rag_service import RAGService, compute_function_coverage


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


def test_search_doc_type_filter():
    rag = RAGService(Settings(mock_rag=True, knowledge_base_path="./data/knowledge_base"))
    results = rag.search_similar_projects("chassis", top_k=5, doc_type_filter=["summary"])
    assert all((h.get("metadata") or {}).get("doc_type") == "summary" for h in results)


def test_real_search_empty_returns_no_mock_fallback(monkeypatch, tmp_path):
    kb = tmp_path / "kb"
    kb.mkdir()
    chroma = tmp_path / "chroma"
    rag = RAGService(
        Settings(mock_rag=False, knowledge_base_path=str(kb), chroma_path=str(chroma))
    )

    class FakeChroma:
        def search(self, query: str, top_k: int = 5):
            return []

        def count(self):
            return 0

        def get_metadata(self, doc_id: str):
            return None

    monkeypatch.setattr(rag, "_get_chroma", lambda: FakeChroma())
    assert rag.search_similar_projects("MEB chassis", top_k=3) == []


def test_list_documents_mock():
    rag = RAGService(Settings(mock_rag=True, knowledge_base_path="./data/knowledge_base"))
    docs = rag.list_documents()
    assert len(docs) == 3
    statuses = {d["status"] for d in docs}
    assert statuses == {"indexed", "pending", "failed"}


def test_import_skips_unchanged_hash(tmp_path, monkeypatch):
    kb = tmp_path / "kb" / "proj_a"
    kb.mkdir(parents=True)
    doc = kb / "rfq.docx"
    doc.write_bytes(b"fake docx content for hash test")

    chroma = tmp_path / "chroma"
    rag = RAGService(
        Settings(mock_rag=False, knowledge_base_path=str(tmp_path / "kb"), chroma_path=str(chroma))
    )

    class RecordingChroma:
        def __init__(self):
            self.metas: dict[str, dict] = {}
            self.docs: dict[str, str] = {}

        def add_document(self, doc_id: str, text: str, metadata: dict):
            self.metas[doc_id] = dict(metadata)
            self.docs[doc_id] = text

        def get_metadata(self, doc_id: str):
            return self.metas.get(doc_id)

        def count(self):
            return len(self.docs)

        def search(self, query: str, top_k: int = 5):
            return []

    store = RecordingChroma()
    monkeypatch.setattr(rag, "_get_chroma", lambda: store)
    monkeypatch.setattr(
        rag._parser,
        "extract_text_from_docx",
        lambda _path: "parsed rfq text",
    )

    first = rag.import_documents()
    assert first["new_documents"] == 1
    assert first["skipped"] == 0

    second = rag.import_documents()
    assert second["new_documents"] == 0
    assert second["skipped"] == 1


def test_mock_stats_includes_function_coverage():
    rag = RAGService(Settings(mock_rag=True, knowledge_base_path="./data/knowledge_base"))
    stats = rag.get_stats()
    assert stats["total_documents"] > 0
    assert "function_coverage" in stats
    assert stats["function_coverage"]["Chassis"] >= 0.9
