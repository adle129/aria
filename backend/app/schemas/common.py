from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    code: int = 200
    data: T | None = None
    msg: str | None = None


class HealthResponse(BaseModel):
    status: str = Field(..., examples=["ok"])
    version: str
    model: str
    embedding_model: str
    mock_llm: bool = False
    mock_rag: bool = False
