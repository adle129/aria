from app.config import Settings
from app.services.rag_service import RAGService


def test_knowledge_stats(client):
    response = client.get("/api/v1/knowledge/stats")
    assert response.status_code == 200
    data = response.json()["data"]
    assert "total_documents" in data
    assert "total_projects" in data
    assert "total_chunks" in data
    assert "function_coverage" in data


def test_knowledge_stats_mock_has_coverage_values(client):
    response = client.get("/api/v1/knowledge/stats")
    data = response.json()["data"]
    if data.get("mock_rag"):
        assert data["function_coverage"]["Chassis"] >= 0.9
        assert data.get("last_import_at")


def test_knowledge_search(client):
    response = client.post("/api/v1/knowledge/search", json={"query": "MEB chassis", "top_k": 3})
    assert response.status_code == 200
    results = response.json()["data"]["results"]
    assert len(results) == 3
    hit = results[0]
    assert "content" in hit
    assert "similarity_score" in hit
    assert "metadata" in hit
    assert "project_name" in hit["metadata"]
    assert "source_doc" in hit["metadata"]


def test_knowledge_search_empty_query_rejected(client):
    response = client.post("/api/v1/knowledge/search", json={"query": "a"})
    assert response.status_code == 422


def test_knowledge_search_function_filter(client):
    response = client.post(
        "/api/v1/knowledge/search",
        json={"query": "chassis", "top_k": 5, "function_filter": ["PM"]},
    )
    assert response.status_code == 200
    results = response.json()["data"]["results"]
    for hit in results:
        assert "PM" in hit["metadata"].get("functions", [])


def test_knowledge_import(client):
    response = client.post("/api/v1/knowledge/import")
    assert response.status_code == 200
    data = response.json()["data"]
    assert "new_documents" in data
    assert "failed_files" in data
    assert isinstance(data["failed_files"], list)


def test_knowledge_documents(client):
    response = client.get("/api/v1/knowledge/documents")
    assert response.status_code == 200
    docs = response.json()["data"]["documents"]
    assert len(docs) >= 1
    doc = docs[0]
    assert "path" in doc
    assert "status" in doc
    assert "doc_type" in doc


def test_knowledge_search_doc_type_filter(client):
    response = client.post(
        "/api/v1/knowledge/search",
        json={"query": "chassis", "top_k": 5, "doc_type_filter": ["summary"]},
    )
    assert response.status_code == 200
    results = response.json()["data"]["results"]
    for hit in results:
        assert hit["metadata"].get("doc_type") == "summary"


def test_knowledge_mock_real_schema_parity(monkeypatch):
    """Mock mode returns valid RAGHit field set; real mode delegates to index service."""
    mock_rag = RAGService(Settings(mock_rag=True, knowledge_base_path="./data/knowledge_base"))

    query = "MEB chassis"
    mock_hits = mock_rag.search_similar_projects(query, top_k=3)
    assert len(mock_hits) >= 1
    required_keys = {"content", "metadata", "similarity_score"}
    meta_keys = {"project_name", "source_doc", "doc_type"}
    for hit in mock_hits:
        assert required_keys <= set(hit.keys())
        assert meta_keys <= set((hit.get("metadata") or {}).keys())

    # Real mode with empty index (mocked) returns empty list.
    from app.services import knowledge_index_service

    monkeypatch.setattr(
        knowledge_index_service.KnowledgeIndexService,
        "search",
        lambda self, query, **kwargs: [],
    )
    real_rag = RAGService(Settings(mock_rag=False, knowledge_base_path="./data/knowledge_base"))
    real_hits = real_rag.search_similar_projects(query, top_k=3)
    assert real_hits == []

