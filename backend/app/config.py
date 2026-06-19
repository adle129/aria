from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_version: str = "1.0.0"
    log_level: str = "INFO"

    database_url: str = "postgresql://aria_admin:localdev123@localhost:5432/aria_db"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:14b"
    embedding_model: str = "nomic-embed-text"
    mock_llm: bool = True
    mock_rag: bool = True

    prompt_version: str = "v1"
    chroma_path: str = "./data/chroma_db"
    upload_path: str = "./data/uploads"
    output_path: str = "./data/outputs"
    knowledge_base_path: str = "./data/knowledge_base"
    template_path: str = "./data/templates"


@lru_cache
def get_settings() -> Settings:
    return Settings()
