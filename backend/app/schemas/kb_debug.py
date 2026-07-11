from typing import Any

from pydantic import BaseModel, Field


class KBDebugStatusResponse(BaseModel):
    kb_debug_enabled: bool
    aria_ui_profile: str
    mock_rag: bool
    corpus_path: str
    corpus_exists: bool
    indexed_chunks: int
    last_index_at: str | None = None
    last_corpus_path: str | None = None
    embedding_model: str
    ollama_reachable: bool
    embedding_model_ready: bool
    ollama_error: str | None = None


class KBDebugPreviewRequest(BaseModel):
    corpus_path: str | None = None


class KBDebugFileRequest(BaseModel):
    filename: str = Field(..., min_length=1, max_length=500)
    corpus_path: str | None = None


class KBDebugIndexRequest(BaseModel):
    corpus_path: str | None = None
    filename: str | None = None
    clear: bool = True


class KBDebugSearchRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=500)
    top_k: int = Field(default=5, ge=1, le=20)
    function_filter: list[str] | None = None
    doc_type_filter: list[str] | None = None


class KBDebugFeedbackRequest(BaseModel):
    feedback_type: str
    source_context: str = "chunk_inspector"
    chunk_id: str | None = None
    query: str | None = None
    comment: str | None = None
    snapshot: dict[str, Any] = Field(default_factory=dict)


class KBDebugEvalQuery(BaseModel):
    query: str = Field(..., min_length=2, max_length=500)
    expected_source_doc: str | None = None
    expected_area: str | None = None
    expected_doc_types: list[str] | None = None
    min_score: float = 0.3


class KBDebugEvalRequest(BaseModel):
    queries: list[KBDebugEvalQuery] = Field(default_factory=list)
    top_k: int = Field(default=3, ge=1, le=10)
