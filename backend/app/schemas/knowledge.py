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
    section_path: str | None = None
    section_depth: int | None = None

    model_config = {"extra": "allow"}


class RAGHit(BaseModel):
    content: str
    metadata: RAGHitMetadata | dict[str, Any] = Field(default_factory=dict)
    similarity_score: float = Field(..., ge=0.0, le=1.0)


class KnowledgeSearchGroup(BaseModel):
    engagement_id: str | None = None
    project_name: str
    similarity_score: float = Field(..., ge=0.0, le=1.0)
    source_doc: str | None = None
    metadata: RAGHitMetadata | dict[str, Any] = Field(default_factory=dict)
    hits: list[RAGHit] = Field(default_factory=list)


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=500)
    top_k: int = Field(default=5, ge=1, le=20)
    function_filter: list[str] | None = None
    doc_type_filter: list[str] | None = None


class KnowledgeSearchResponse(BaseModel):
    groups: list[KnowledgeSearchGroup] = Field(default_factory=list)
    results: list[RAGHit] = Field(default_factory=list)
    insufficient_evidence: bool = False


class KnowledgeDocumentItem(BaseModel):
    path: str
    project_name: str
    doc_type: str
    status: str
    file_size_bytes: int | None = None
    error: str | None = None
    engagement_id: str | None = None
    customer: str | None = None
    year: int | None = None
    functions: list[str] = Field(default_factory=list)
    metadata_summary: str | None = None


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
    customer: str | None = None
    year: int | None = None
    functions: list[str] = Field(default_factory=list)
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


class KnowledgeImportBatchItem(BaseModel):
    import_id: str
    job_id: str | None = None
    triggered_by: str | None = None
    batch_id: str | None = None
    mode: str
    status: str
    generation_id: str | None = None
    new_documents: int = 0
    new_chunks: int = 0
    skipped: int = 0
    failed_count: int = 0
    failed_files: list[dict[str, str]] = Field(default_factory=list)
    engagements: list[dict[str, Any]] = Field(default_factory=list)
    error_message: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    created_at: str | None = None


class EngagementAuditItem(BaseModel):
    engagement_id: str
    project_name: str
    customer: str | None = None
    year: int | None = None
    functions: list[str] = Field(default_factory=list)
    tier: str | None = None
    index_status: str
    content_hash: str | None = None
    uploaded_at: str | None = None
    uploaded_by: str | None = None
    last_indexed_at: str | None = None
    last_error: str | None = None
    folder_path: str
    metadata_complete: bool = False


class EngagementMetadataUpdate(BaseModel):
    """Full business metadata update (all fields required for RFQ ranking quality)."""

    project_name: str = Field(..., min_length=1, max_length=256)
    customer: str = Field(..., min_length=1, max_length=256)
    year: int = Field(..., ge=1990, le=2100)
    functions: list[str] = Field(..., min_length=1)


class KnowledgeStatsResponse(BaseModel):
    total_documents: int
    total_chunks: int
    total_projects: int
    last_import_at: str | None = None
    active_generation: str | None = None
    function_coverage: dict[str, float] = Field(default_factory=dict)
    mock_rag: bool | None = None