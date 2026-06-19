from fastapi import APIRouter

from app.config import get_settings
from app.schemas.common import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        version=settings.app_version,
        model=settings.ollama_model,
        embedding_model=settings.embedding_model,
        mock_llm=settings.mock_llm,
        mock_rag=settings.mock_rag,
    )
