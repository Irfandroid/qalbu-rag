from collections.abc import Mapping

from fastapi import HTTPException

from app.core.config import get_settings
from app.database.queries import SupabaseQuranRepository
from app.database.supabase import get_supabase
from app.providers.embeddings.jina import JinaEmbeddingProvider
from app.providers.llm.gemini import GeminiProvider
from app.quran.catalog import CHUNK_TYPES, CORPUS
from app.rag.citation_validator import CitationValidator
from app.rag.pipeline import QalbuRAG
from app.rag.retriever import QuranRetriever
from app.safety.guardrails import SafetyGuardrails


async def get_rag() -> QalbuRAG:
    settings = get_settings()
    if not settings.configured_for_rag:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "RAG_UNAVAILABLE",
                "message": "Gemini, Jina, dan Supabase server wajib dikonfigurasi.",
            },
        )
    supabase = await get_supabase(settings)
    repository = SupabaseQuranRepository(supabase, settings.quran_corpus)
    embeddings = JinaEmbeddingProvider(
        settings.jina_api_key or "",
        settings.jina_embedding_model,
        settings.embedding_dimensions,
        settings.request_timeout_seconds,
    )
    llm = GeminiProvider(
        settings.gemini_api_key or "",
        settings.gemini_model,
        settings.request_timeout_seconds,
    )
    return QalbuRAG(
        SafetyGuardrails(),
        QuranRetriever(
            embeddings,
            repository,
            settings.min_retrieval_score,
            settings.top_k_retrieval,
            settings.retrieval_parent_k,
        ),
        llm,
        CitationValidator(),
        settings.rag_cache_version,
        settings.qalbu_profile,
        settings.crisis_line,
        settings.crisis_line_label,
        settings.max_context_tokens,
    )


async def get_dataset_child_counts() -> dict[str, int] | None:
    settings = get_settings()
    if settings.quran_corpus != CORPUS:
        return None
    if not settings.supabase_url or not settings.supabase_server_key:
        return None
    supabase = await get_supabase(settings)
    counts = {chunk_type: 0 for chunk_type in CHUNK_TYPES}
    start = 0
    while True:
        response = await (
            supabase.table("quran_chunks")
            .select("chunk_type")
            .eq("corpus", settings.quran_corpus)
            .range(start, start + 999)
            .execute()
        )
        rows = response.data or []
        for row in rows:
            if not isinstance(row, Mapping):
                continue
            chunk_type = row.get("chunk_type")
            if isinstance(chunk_type, str) and chunk_type in counts:
                counts[chunk_type] += 1
        if len(rows) < 1000:
            return counts
        start += 1000
