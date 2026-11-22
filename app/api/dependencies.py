"""FastAPI dependency wiring: RAG pipeline and read-only dataset lookups."""

from fastapi import HTTPException, Path

from app.core.config import get_settings
from app.database.postgres import get_pool
from app.database.queries import PostgresQuranRepository, chunk_type_counts
from app.models.quran import QuranDocument
from app.providers.embeddings.ollama import OllamaEmbeddingProvider
from app.providers.llm.ollama import OllamaProvider
from app.quran.catalog import (
    CHUNK_TYPES,
    CORPUS,
    build_catalog,
    daily_date_in_timezone,
    parent_id,
    select_verse_of_day,
)
from app.rag.citation_validator import CitationValidator, is_official_kemenag
from app.rag.pipeline import QalbuRAG
from app.rag.retriever import QuranRetriever
from app.safety.guardrails import SafetyGuardrails


async def get_rag() -> QalbuRAG:
    """Build the full chat pipeline; reject requests without a database."""
    settings = get_settings()
    if not settings.configured_for_rag:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "RAG_UNAVAILABLE",
                "message": "DATABASE_URL wajib dikonfigurasi.",
            },
        )
    pool = await get_pool(settings)
    repository = PostgresQuranRepository(pool, settings.quran_corpus)
    embeddings = OllamaEmbeddingProvider(
        settings.ollama_base_url,
        settings.ollama_embedding_model,
        settings.embedding_dimensions,
        settings.request_timeout_seconds,
    )
    llm = OllamaProvider(
        settings.ollama_base_url,
        settings.ollama_model,
        settings.request_timeout_seconds,
        num_ctx=settings.ollama_num_ctx,
    )
    retriever = QuranRetriever(
        embeddings,
        repository,
        settings.min_retrieval_score,
        settings.top_k_retrieval,
        settings.retrieval_parent_k,
    )
    return QalbuRAG(
        SafetyGuardrails(),
        retriever,
        llm,
        CitationValidator(),
        settings.rag_cache_version,
        settings.qalbu_profile,
        settings.crisis_line,
        settings.crisis_line_label,
        settings.max_context_tokens,
    )


async def get_dataset_child_counts() -> dict[str, int] | None:
    """Count chunk types for the active corpus, or ``None`` when unavailable."""
    settings = get_settings()
    if settings.quran_corpus != CORPUS or not settings.configured_for_rag:
        return None
    counts = {chunk_type: 0 for chunk_type in CHUNK_TYPES}
    counts.update(
        await chunk_type_counts(await get_pool(settings), settings.quran_corpus)
    )
    return counts


def _dataset_unavailable(message: str) -> HTTPException:
    return HTTPException(
        status_code=503,
        detail={"code": "DATASET_DETAIL_UNAVAILABLE", "message": message},
    )


async def _get_active_document(verse_key: str) -> QuranDocument:
    """Fetch one verse and require official Kemenag provenance."""
    settings = get_settings()
    if settings.quran_corpus != CORPUS:
        raise _dataset_unavailable(f"Dataset detail requires active corpus {CORPUS}.")
    if not settings.configured_for_rag:
        raise _dataset_unavailable("Active Quran source is not configured.")

    try:
        pool = await get_pool(settings)
        repository = PostgresQuranRepository(pool, settings.quran_corpus)
        documents = await repository.get_documents(
            [parent_id(settings.quran_corpus, verse_key)]
        )
    except Exception as exc:
        raise _dataset_unavailable("Active Quran source is temporarily unavailable.") from exc

    if not documents:
        raise HTTPException(
            status_code=404,
            detail={"code": "VERSE_NOT_FOUND", "message": "Ayat tidak ditemukan."},
        )

    document = documents[0]
    if not is_official_kemenag(document.metadata):
        raise _dataset_unavailable("Ayat belum memiliki provenance sumber resmi yang valid.")
    return document


async def get_dataset_document(
    surah: int = Path(ge=1, le=114),
    ayah: int = Path(ge=1),
) -> QuranDocument:
    return await _get_active_document(f"{surah}:{ayah}")


async def get_daily_verse_document() -> QuranDocument:
    """Resolve today's manifest-selected verse through the official source."""
    try:
        catalog = build_catalog()
    except Exception as exc:
        raise _dataset_unavailable("Active Quran corpus manifest is unavailable.") from exc
    verse_keys = [verse["verse_key"] for verse in catalog["verses"]]
    key = select_verse_of_day(verse_keys, daily_date_in_timezone())
    return await _get_active_document(key)
