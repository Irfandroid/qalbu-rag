import logging
import time

from app.models.rag import RetrievalResult
from app.providers.embeddings.base import EmbeddingProvider
from app.quran.repository import QuranRepository
from app.rag.query_processing import enrich_query


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
        embedding_ms = round((time.perf_counter() - embedding_started) * 1000, 2)
        vector_started = time.perf_counter()
        results = await self.repository.match_chunks(embedding, self.candidate_k)
        vector_ms = round((time.perf_counter() - vector_started) * 1000, 2)
        accepted = [result for result in results if result.score >= self.min_score]
        # Keep only the strongest child for each parent. This prevents repeated
        # tafsir/translation children from consuming the whole LLM context.
        by_parent: dict[str, RetrievalResult] = {}
        for result in accepted:
            current = by_parent.get(result.parent_id)
            if current is None or result.score > current.score:
                by_parent[result.parent_id] = result
        parents = sorted(
            by_parent.values(),
            key=lambda result: result.score,
            reverse=True,
        )[: self.parent_k]
        logging.getLogger(__name__).info(
            "retrieval request_id=%s themes=%s vector_threshold=%s "
            "embedding_ms=%s vector_ms=%s scores=%s parent_scores=%s "
            "parents=%s embedding_model=%s",
            request_id,
            themes,
            self.min_score,
            embedding_ms,
            vector_ms,
            [round(result.score, 4) for result in results],
            [round(result.score, 4) for result in parents],
            [result.parent_id for result in parents],
            getattr(self.embeddings, "model", "unknown"),
        )
        return parents
