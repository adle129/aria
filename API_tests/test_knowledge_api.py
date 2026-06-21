from app.config import Settings
from app.services.rag_service import RAGService


def test_knowledge_stats(client):
    response = client.get("/api/v1/knowledge/stats")
    assert response.status_code == 200
    data = response.json()["data"]
    assert "total_documents" in data
    assert "total_projects" in data


def test_knowledge_search(client):
    response = client.post("/api/v1/knowledge/search", json={"query": "MEB chassis", "top_k": 3})
    assert response.status_code == 200
    results = response.json()["data"]["results"]
    assert len(results) == 3


def test_knowledge_search_empty_query_rejected(client):
    response = client.post("/api/v1/knowledge/search", json={"query": "a"})
    assert response.status_code == 422


def test_knowledge_import(client):
    response = client.post("/api/v1/knowledge/import")
    assert response.status_code == 200
    assert "new_documents" in response.json()["data"]
