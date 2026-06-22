from app.config import Settings
from app.services.rag_service import RAGService, compute_function_coverage


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


def test_mock_stats_includes_function_coverage():
    rag = RAGService(Settings(mock_rag=True, knowledge_base_path="./data/knowledge_base"))
    stats = rag.get_stats()
    assert stats["total_documents"] > 0
    assert "function_coverage" in stats
    assert stats["function_coverage"]["Chassis"] >= 0.9
