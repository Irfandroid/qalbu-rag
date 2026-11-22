from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    database_url: str | None = None
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:3b-instruct"
    ollama_embedding_model: str = "embeddinggemma"
    ollama_num_ctx: int = 2048
    quran_corpus: str = Field(
        default="qalbu-kemenag-v1",
        validation_alias="QALBU_CORPUS",
        min_length=1,
    )
    embedding_dimensions: int = 768
    kemenag_api_base_url: str = "https://quran-api.lpmqkemenag.id/alquran/data"
    kemenag_username: str | None = None
    kemenag_password: str | None = None
    kemenag_token: str | None = None
    min_retrieval_score: float = 0.32
    top_k_retrieval: int = 15
    retrieval_parent_k: int = 4
    max_context_tokens: int = 1800
    request_timeout_seconds: float = 240
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
                "EMBEDDING_DIMENSIONS must remain 768 until the pgvector column "
                "and match_quran_chunks function are migrated together."
            )
        return self

    @property
    def configured_for_rag(self) -> bool:
        return bool(self.database_url)

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.allowed_origins.split(",")
            if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
