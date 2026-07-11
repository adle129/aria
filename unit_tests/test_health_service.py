from app.config import Settings
from app.services.health_service import build_production_warnings


def test_r1_profile_flags_mock_and_inline_worker():
    settings = Settings(
        aria_ui_profile="r1",
        mock_llm=True,
        mock_rag=True,
        task_worker_inline=True,
        kb_debug_enabled=True,
        auth_enabled=True,
        jwt_secret="change-me-in-production",
    )
    warnings = build_production_warnings(
        settings,
        {"ollama_reachable": True, "ollama_model_ready": True, "embedding_model_ready": True},
    )
    assert any("MOCK_LLM" in w for w in warnings)
    assert any("MOCK_RAG" in w for w in warnings)
    assert any("TASK_WORKER_INLINE" in w for w in warnings)
    assert any("JWT_SECRET" in w for w in warnings)


def test_production_r1_clean_when_ollama_ready():
    settings = Settings(
        aria_ui_profile="r1",
        mock_llm=False,
        mock_rag=False,
        task_worker_inline=False,
        kb_debug_enabled=False,
        auth_enabled=True,
        jwt_secret="a" * 64,
    )
    warnings = build_production_warnings(
        settings,
        {"ollama_reachable": True, "ollama_model_ready": True, "embedding_model_ready": True},
    )
    assert warnings == []


def test_ollama_unreachable_warning_when_not_mock():
    settings = Settings(mock_llm=False, mock_rag=False, ollama_base_url="http://127.0.0.1:11434")
    warnings = build_production_warnings(
        settings,
        {"ollama_reachable": False, "ollama_error": "connection refused"},
    )
    assert any("Ollama" in w for w in warnings)
