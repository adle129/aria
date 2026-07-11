from fastapi import APIRouter

from app.config import get_settings
from app.schemas.common import HealthResponse
from app.services.disk_guard_service import DiskGuardService
from app.services.health_service import build_production_warnings
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
    disk = DiskGuardService(settings).status()
    return HealthResponse(
        status="ok",
        version=settings.app_version,
        deploy_sha=(settings.deploy_sha or "unknown").strip() or "unknown",
        packaged_at=(settings.packaged_at or "").strip() or None,
        model=settings.ollama_model,
        embedding_model=settings.embedding_model,
        mock_llm=settings.mock_llm,
        mock_rag=settings.mock_rag,
        ollama_reachable=probe["ollama_reachable"],
        ollama_model_ready=probe["ollama_model_ready"],
        embedding_model_ready=probe["embedding_model_ready"],
        ollama_error=probe["ollama_error"],
        kb_debug_enabled=settings.kb_debug_enabled,
        aria_ui_profile=settings.aria_ui_profile,
        auth_enabled=settings.auth_enabled,
        production_warnings=build_production_warnings(settings, probe),
        data_volume=disk["data_volume"],
        temp_volume=disk["temp_volume"],
    )
