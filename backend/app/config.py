from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.utils.paths import resolve_data_path


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_version: str = "1.0.0"
    # Baked at image build (DEPLOY_SHA); used to verify staging/prod rollouts
    deploy_sha: str = "unknown"
    packaged_at: str = ""
    log_level: str = "INFO"

    database_url: str = "postgresql://aria_admin:localdev123@localhost:5432/aria_db"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:14b"
    ollama_llm_timeout_seconds: int = 600
    embedding_model: str = "nomic-embed-text"
    embedding_max_chars: int = 2400
    embedding_batch_size: int = 16
    mock_llm: bool = True
    mock_rag: bool = True

    auth_enabled: bool = False
    jwt_secret: str = "change-me-in-production"
    jwt_expire_hours: int = 24

    ollama_max_concurrent: int = 1
    ollama_global_scheduling_enabled: bool = True
    ollama_lease_ttl_seconds: int = 30
    ollama_lease_heartbeat_seconds: int = 10
    ollama_lease_query_wait_timeout_seconds: int = 30
    ollama_lease_worker_wait_timeout_seconds: int = 600
    rag_similarity_threshold: float = 0.65
    task_worker_inline: bool = False
    task_worker_poll_seconds: float = 2.0
    task_job_avg_seconds: int = 120
    task_job_stale_seconds: int = 900
    task_job_cancel_stale_seconds: int = 120
    task_max_queue_size: int = 20
    kb_async_index_enabled: bool = True
    disk_warning_percent: float = 80.0
    disk_write_protect_percent: float = 90.0
    disk_min_free_bytes: int = 256 * 1024 * 1024
    upload_max_archive_bytes: int = 100 * 1024 * 1024
    upload_max_entries: int = 500
    upload_max_single_file_bytes: int = 50 * 1024 * 1024
    upload_max_expanded_bytes: int = 500 * 1024 * 1024
    upload_max_compression_ratio: float = 100.0
    upload_stream_chunk_bytes: int = 1024 * 1024

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
    manpower_baselines_path: str = "./data/manpower_baselines.json"
    dimension_baseline_path: str = "./data/config/dimension_baseline.v1.json"
    knowledge_vector_namespace: str = "production"
    template_path: str = "./data/templates"
    samples_rfq_path: str = "/app/samples/rfq"

    @model_validator(mode="after")
    def _kb_debug_dev_only(self) -> "Settings":
        if self.kb_debug_enabled and self.aria_ui_profile != "dev":
            self.kb_debug_enabled = False
        return self

    @model_validator(mode="after")
    def _validate_disk_thresholds(self) -> "Settings":
        if not (
            0
            <= self.disk_warning_percent
            < self.disk_write_protect_percent
            <= 100
        ):
            raise ValueError(
                "disk thresholds must satisfy 0 <= warning < write_protect <= 100"
            )
        return self

    @model_validator(mode="after")
    def _validate_upload_limits(self) -> "Settings":
        positive_limits = (
            self.upload_max_archive_bytes,
            self.upload_max_entries,
            self.upload_max_single_file_bytes,
            self.upload_max_expanded_bytes,
            self.upload_max_compression_ratio,
            self.upload_stream_chunk_bytes,
        )
        if any(limit <= 0 for limit in positive_limits):
            raise ValueError("upload limits must all be positive")
        if (
            self.upload_max_single_file_bytes
            > self.upload_max_expanded_bytes
        ):
            raise ValueError(
                "single upload file limit cannot exceed expanded ZIP limit"
            )
        return self

    @model_validator(mode="after")
    def _normalize_data_paths(self) -> "Settings":
        self.upload_path = str(resolve_data_path(self.upload_path))
        self.output_path = str(resolve_data_path(self.output_path))
        self.chroma_path = str(resolve_data_path(self.chroma_path))
        self.knowledge_base_path = str(resolve_data_path(self.knowledge_base_path))
        self.template_path = str(resolve_data_path(self.template_path))
        if not Path(self.manpower_baselines_path).is_absolute():
            self.manpower_baselines_path = str(resolve_data_path(self.manpower_baselines_path))
        if not Path(self.dimension_baseline_path).is_absolute():
            self.dimension_baseline_path = str(resolve_data_path(self.dimension_baseline_path))
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
