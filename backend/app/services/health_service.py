from typing import Any

from app.config import Settings


def build_production_warnings(settings: Settings, probe: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    profile = (settings.aria_ui_profile or "").strip().lower()

    if profile == "r1":
        if settings.mock_llm:
            warnings.append("MOCK_LLM=true：R1 验收须为 false")
        if settings.mock_rag:
            warnings.append("MOCK_RAG=true：R1 验收须为 false")
        if settings.kb_debug_enabled:
            warnings.append("KB_DEBUG_ENABLED=true：生产 R1 须为 false")
        if settings.task_worker_inline:
            warnings.append("TASK_WORKER_INLINE=true：生产须独立 worker 进程")

    if not settings.mock_llm:
        if not probe.get("ollama_reachable"):
            warnings.append(f"Ollama 不可达：{probe.get('ollama_error') or settings.ollama_base_url}")
        elif not probe.get("ollama_model_ready"):
            warnings.append(f"LLM 模型未就绪：{settings.ollama_model}")

    if not settings.mock_rag:
        if probe.get("ollama_reachable") and not probe.get("embedding_model_ready"):
            warnings.append(f"Embedding 模型未就绪：{settings.embedding_model}")

    if settings.auth_enabled and settings.jwt_secret.strip() in {
        "",
        "change-me-in-production",
        "change-me-with-openssl-rand-hex-32",
    }:
        warnings.append("JWT_SECRET 仍为占位值，请部署前更换")

    return warnings
