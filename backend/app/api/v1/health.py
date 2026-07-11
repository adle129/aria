from fastapi import APIRouter

from app.config import get_settings
from app.schemas.common import HealthResponse
from app.services.ollama_service import probe_ollama

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    settings = get_settings()
    probe = probe_ollama(
        settings.ollama_base_url,
        settings.ollama_model,
        settings.embedding_model,
    )
    return HealthResponse(
        status="ok",
        version=settings.app_version,
        model=settings.ollama_model,
        embedding_model=settings.embedding_model,
        mock_llm=settings.mock_llm,
        mock_rag=settings.mock_rag,
        ollama_reachable=probe["ollama_reachable"],
        ollama_model_ready=probe["ollama_model_ready"],
        embedding_model_ready=probe["embedding_model_ready"],
        ollama_error=probe["ollama_error"],
    )
