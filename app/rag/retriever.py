"""Embedding search, parent de-duplication, and score thresholding."""

import logging
import time

from app.models.rag import RetrievalResult
from app.providers.embeddings.base import EmbeddingProvider
from app.quran.repository import QuranRepository
from app.rag.query_processing import enrich_query

logger = logging.getLogger(__name__)

# One verse can produce several children (arabic/translation/tafsir/themes).
# Oversample children so repeated parents cannot consume every retrieval slot.
PARENT_OVERSAMPLE_FACTOR = 4


class QuranRetriever:
    def __init__(
        self,
        embeddings: EmbeddingProvider,
        repository: QuranRepository,
        min_score: float = 0.55,
        candidate_k: int = 12,
        parent_k: int = 3,
    ) -> None:
        self.embeddings = embeddings
        self.repository = repository
        self.min_score = min_score
        self.candidate_k = candidate_k
        self.parent_k = parent_k

    async def search(self, query: str, request_id: str | None = None) -> list[RetrievalResult]:
        processed_query, themes = enrich_query(query)

        embedding_started = time.perf_counter()
        embedding = await self.embeddings.embed_query(processed_query)
        embedding_ms = _elapsed_ms(embedding_started)

        child_candidate_k = max(self.candidate_k, self.parent_k * PARENT_OVERSAMPLE_FACTOR)
        vector_started = time.perf_counter()
        results = await self.repository.match_chunks(embedding, child_candidate_k)
        vector_ms = _elapsed_ms(vector_started)

        accepted = [result for result in results if result.score >= self.min_score]
        parents = _rank_parents(_strongest_child_per_parent(accepted), self.parent_k)

        logger.info(
            "retrieval request_id=%s themes=%s vector_threshold=%s "
            "embedding_ms=%s vector_ms=%s scores=%s parent_scores=%s "
            "parents=%s child_candidate_k=%s embedding_model=%s",
            request_id,
            themes,
            self.min_score,
            embedding_ms,
            vector_ms,
            [round(result.score, 4) for result in results],
            [round(result.score, 4) for result in parents],
            [result.parent_id for result in parents],
            child_candidate_k,
            getattr(self.embeddings, "model", "unknown"),
        )
        return parents


def _strongest_child_per_parent(
    results: list[RetrievalResult],
) -> list[RetrievalResult]:
    """Keep the best-scoring child for each parent to bound LLM context."""
    by_parent: dict[str, RetrievalResult] = {}
    for result in results:
        current = by_parent.get(result.parent_id)
        if current is None or result.score > current.score:
            by_parent[result.parent_id] = result
    return list(by_parent.values())


def _rank_parents(results: list[RetrievalResult], limit: int) -> list[RetrievalResult]:
    return sorted(results, key=lambda result: result.score, reverse=True)[:limit]


def _elapsed_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 2)
