from fastapi import HTTPException

from app.core.config import get_settings
from app.database.queries import SupabaseQuranRepository
from app.database.supabase import get_supabase
from app.llm.base import LLMProvider
from app.llm.groq import GroqProvider
from app.llm.ollama import OllamaProvider
from app.rag.citation_validator import CitationValidator
from app.rag.embeddings import LocalE5EmbeddingProvider
from app.rag.parent_retriever import ParentRetriever
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
                "message": (
                    "Qalbu needs its configured LLM, SUPABASE_URL, and "
                    "SUPABASE_SECRET_KEY before chat can run."
                ),
            },
        )
    repository = SupabaseQuranRepository(await get_supabase(settings))
    embeddings = LocalE5EmbeddingProvider(settings.embedding_model, settings.embedding_dimensions)
    llm: LLMProvider
    if settings.llm_provider == "ollama":
        llm = OllamaProvider(
            settings.ollama_base_url,
            settings.ollama_model,
            settings.ollama_num_ctx,
            settings.ollama_keep_alive,
        )
    elif settings.llm_provider == "groq":
        llm = GroqProvider(settings.groq_api_key or "", settings.groq_model)
    else:
        raise HTTPException(
            status_code=503,
            detail={"code": "RAG_UNAVAILABLE", "message": "Unsupported LLM_PROVIDER."},
        )
    return QalbuRAG(
        SafetyGuardrails(),
        QuranRetriever(
            embeddings,
            repository,
            settings.min_retrieval_score,
            settings.retrieval_candidate_k,
            settings.retrieval_parent_k,
        ),
        ParentRetriever(repository),
        llm,
        CitationValidator(),
        settings.rag_cache_version,
        settings.qalbu_profile,
        settings.crisis_line,
        settings.crisis_line_label,
    )
