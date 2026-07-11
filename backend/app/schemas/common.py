from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    code: int = 200
    data: T | None = None
    msg: str | None = None


class DiskVolumeHealth(BaseModel):
    volume: str
    total_bytes: int
    used_bytes: int
    free_bytes: int
    usage_percent: float
    warning: bool
    write_protected: bool


class HealthResponse(BaseModel):
    status: str = Field(..., examples=["ok"])
    version: str
    model: str
    embedding_model: str
    mock_llm: bool = False
    mock_rag: bool = False
    ollama_reachable: bool = False
    ollama_model_ready: bool = False
    embedding_model_ready: bool = False
    ollama_error: str | None = None
    kb_debug_enabled: bool = False
    aria_ui_profile: str = "experience"
    auth_enabled: bool = False
    production_warnings: list[str] = Field(default_factory=list)
    data_volume: DiskVolumeHealth
    temp_volume: DiskVolumeHealth
