from typing import Any, Literal

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
    doc_type_filter: list[str] | None = None


class KnowledgeSearchResponse(BaseModel):
    results: list[RAGHit]


class KnowledgeDocumentItem(BaseModel):
    path: str
    project_name: str
    doc_type: str
    status: str
    file_size_bytes: int | None = None
    error: str | None = None


class KnowledgeDocumentsResponse(BaseModel):
    documents: list[KnowledgeDocumentItem]


class EngagementCompletenessData(BaseModel):
    tier: Literal["gold", "silver", "copper"]
    indexable: bool
    missing: list[str] = Field(default_factory=list)
    automation_impacts: list[str] = Field(default_factory=list)


class EngagementUploadPackResult(EngagementCompletenessData):
    engagement_id: str
    project_name: str | None = None
    status: Literal["stored"]
    stored: bool
    path: str
    files: list[str] = Field(default_factory=list)
    errors: list[dict[str, Any]] = Field(default_factory=list)


class EngagementImportResult(EngagementCompletenessData):
    engagement_id: str
    status: Literal["indexed", "failed"]
    error: str | None = None


class KnowledgeImportResponse(BaseModel):
    new_documents: int
    new_chunks: int
    skipped: int
    failed_files: list[dict[str, str]] = Field(default_factory=list)
    last_import_at: str | None = None
    engagements: list[EngagementImportResult] = Field(default_factory=list)


class KnowledgeStatsResponse(BaseModel):
    total_documents: int
    total_chunks: int
    total_projects: int
    last_import_at: str | None = None
    active_generation: str | None = None
    function_coverage: dict[str, float] = Field(default_factory=dict)
    mock_rag: bool | None = None
