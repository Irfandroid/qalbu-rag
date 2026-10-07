from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.5-flash-lite"
    supabase_url: str | None = None
    supabase_secret_key: str | None = None
    supabase_service_role_key: str | None = None
    jina_api_key: str | None = None
    jina_embedding_model: str = "jina-embeddings-v5-text-small"
    embedding_dimensions: int = 768
    kemenag_api_base_url: str = "https://quran-api.lpmqkemenag.id/alquran/data"
    kemenag_username: str | None = None
    kemenag_password: str | None = None
    kemenag_token: str | None = None
    min_retrieval_score: float = 0.32
    top_k_retrieval: int = 15
    retrieval_parent_k: int = 4
    max_context_tokens: int = 1800
    request_timeout_seconds: float = 30
    chat_rate_limit_per_minute: int = 10
    rag_cache_version: str = "qalbu-mvp-v1"
    allowed_origins: str = "http://localhost:8000"
    qalbu_profile: str = "local"
    crisis_line: str | None = None
    crisis_line_label: str = "Layanan darurat setempat"
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
        return bool(
            self.gemini_api_key
            and self.jina_api_key
            and self.supabase_url
            and self.supabase_server_key
        )

    @property
    def supabase_server_key(self) -> str | None:
        """Prefer modern secret key; retain legacy service_role compatibility."""
        return self.supabase_secret_key or self.supabase_service_role_key


@lru_cache
def get_settings() -> Settings:
    return Settings()
