from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_version: str = "1.0.0"
    log_level: str = "INFO"

    database_url: str = "postgresql://aria_admin:localdev123@localhost:5432/aria_db"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:14b"
    ollama_llm_timeout_seconds: int = 600
    embedding_model: str = "nomic-embed-text"
    embedding_max_chars: int = 2400
    mock_llm: bool = True
    mock_rag: bool = True

    # UI / deployment (see docs/R1/kb-debug-ui-spec.md)
    aria_ui_profile: str = "experience"  # dev | experience | r1 | full
    kb_debug_enabled: bool = False  # true only when aria_ui_profile=dev

    validation_corpus_path: str = r"E:/AI文档项目/RE_ 报价AI需求沟通"
    feedback_path: str = "./data/app/feedback/debug_feedback.jsonl"

    prompt_version: str = "v1"
    chroma_path: str = "./data/chroma_db"
    upload_path: str = "./data/uploads"
    output_path: str = "./data/outputs"
    knowledge_base_path: str = "./data/knowledge_base"
    template_path: str = "./data/templates"
    samples_rfq_path: str = "/app/samples/rfq"

    @model_validator(mode="after")
    def _kb_debug_dev_only(self) -> "Settings":
        if self.kb_debug_enabled and self.aria_ui_profile != "dev":
            self.kb_debug_enabled = False
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
