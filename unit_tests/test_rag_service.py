from app.config import Settings
from app.services.rag_service import RAGService


def test_mock_search_returns_top_k():
    rag = RAGService(Settings(mock_rag=True, knowledge_base_path="./data/knowledge_base"))
    results = rag.search_similar_projects("MEB chassis", top_k=2)
    assert len(results) == 2
    assert results[0]["similarity_score"] >= results[1]["similarity_score"]


def test_build_comparison_table_has_confidence():
    rag = RAGService(Settings(mock_rag=True, knowledge_base_path="./data/knowledge_base"))
    docs = rag.search_similar_projects("chassis", top_k=3)
    table = rag.build_comparison_table({"project_name": "test"}, docs)
    assert table["overall_confidence"] in {"高", "中", "低"}
    assert len(table["projects"]) >= 1
    assert "matrix_rows" in table
    assert len(table["matrix_rows"]) >= 5
