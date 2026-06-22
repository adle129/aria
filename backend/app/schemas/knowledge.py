from typing import Any

from pydantic import BaseModel, Field


class RAGHitMetadata(BaseModel):
    project_name: str | None = None
    source_doc: str | None = None
    doc_type: str | None = None
    functions: list[str] = Field(default_factory=list)
    year: int | None = None
    customer: str | None = None
    engagement_id: str | None = None
    chunk_chapter: str | None = None

    model_config = {"extra": "allow"}


class RAGHit(BaseModel):
    content: str
    metadata: RAGHitMetadata | dict[str, Any] = Field(default_factory=dict)
    similarity_score: float = Field(..., ge=0.0, le=1.0)


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=500)
    top_k: int = Field(default=5, ge=1, le=20)
    function_filter: list[str] | None = None


class KnowledgeSearchResponse(BaseModel):
    results: list[RAGHit]


class KnowledgeStatsResponse(BaseModel):
    total_documents: int
    total_chunks: int
    total_projects: int
    last_import_at: str | None = None
    function_coverage: dict[str, float] = Field(default_factory=dict)
    mock_rag: bool | None = None
