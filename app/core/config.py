from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    groq_api_key: str | None = None
    groq_model: str = "openai/gpt-oss-20b"
    llm_provider: str = "ollama"
    ollama_base_url: str = "http://host.docker.internal:11434"
    ollama_model: str = "qwen2.5:3b-instruct"
    # 8 GB CPU profile: smaller KV cache; retain model briefly to avoid a
    # multi-second reload on every consecutive chat turn.
    ollama_num_ctx: int = 2048
    ollama_keep_alive: str = "5m"
    supabase_url: str | None = None
    supabase_secret_key: str | None = None
    supabase_service_role_key: str | None = None
    embedding_provider: str = "local_e5"
    embedding_model: str = "intfloat/multilingual-e5-base"
    embedding_dimensions: int = 768
    min_retrieval_score: float = 0.55
    retrieval_candidate_k: int = 12
    retrieval_parent_k: int = 2
    chat_rate_limit_per_minute: int = 10
    rag_cache_version: str = "sample-v1"
    allowed_origins: str = "http://localhost:8000"
    qf_client_id: str | None = None
    qf_client_secret: str | None = None
    qf_env: str = "prelive"
    qalbu_profile: str = "local"
    crisis_line: str | None = None
    crisis_line_label: str = "Layanan darurat setempat"
    max_queue: int = 3
    log_level: str = "INFO"

    @model_validator(mode="after")
    def embedding_dimension_matches_vector_schema(self) -> "Settings":
        if self.embedding_dimensions != 768:
            raise ValueError(
                "EMBEDDING_DIMENSIONS must remain 768 until the pgvector column, "
                "HNSW index, and match_quran_chunks RPC are migrated together."
            )
        return self

    @property
    def configured_for_rag(self) -> bool:
        llm_ready = (
            bool(self.ollama_base_url and self.ollama_model)
            if self.llm_provider == "ollama"
            else bool(self.groq_api_key)
        )
        return bool(llm_ready and self.supabase_url and self.supabase_server_key)

    @property
    def supabase_server_key(self) -> str | None:
        """Prefer modern secret key; retain legacy service_role compatibility."""
        return self.supabase_secret_key or self.supabase_service_role_key


@lru_cache
def get_settings() -> Settings:
    return Settings()
