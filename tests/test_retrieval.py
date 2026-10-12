import pytest

from app.models.rag import RetrievalResult
from app.rag.retriever import QuranRetriever
from tests.conftest import FakeEmbeddings, FakeRepository


class MultiResultRepository(FakeRepository):
    def __init__(self, results: list[RetrievalResult]) -> None:
        self.results = results
        self.requested_top_k: int | None = None

    async def match_chunks(self, embedding: list[float], top_k: int) -> list[RetrievalResult]:
        self.requested_top_k = top_k
        return self.results[:top_k]


def retrieval_result(parent_id: str, score: float) -> RetrievalResult:
    return RetrievalResult(
        child_id=f"{parent_id}:{score}",
        parent_id=parent_id,
        score=score,
        chunk_type="ayah",
        surah_number=2,
        surah_name="Al-Baqarah",
        ayah_start=286,
        ayah_end=286,
    )


@pytest.mark.asyncio
async def test_retrieval_returns_vector_parent():
    results = await QuranRetriever(FakeEmbeddings(), FakeRepository()).search("hidup berat")
    assert results[0].parent_id == "al-baqarah-286"


@pytest.mark.asyncio
async def test_low_score_results_are_refused():
    results = await QuranRetriever(
        FakeEmbeddings(), FakeRepository(), min_score=0.95
    ).search("aku sedang sedih")
    assert results == []


@pytest.mark.asyncio
async def test_retrieval_deduplicates_parent_and_limits_results():
    repo = MultiResultRepository(
        [
            retrieval_result("al-baqarah-286", 0.91),
            retrieval_result("al-baqarah-286", 0.88),
            retrieval_result("al-balad-4", 0.90),
            retrieval_result("yusuf-87", 0.89),
        ]
    )
    results = await QuranRetriever(FakeEmbeddings(), repo, candidate_k=12, parent_k=2).search(
        "aku sedang berat"
    )
    assert [item.parent_id for item in results] == ["al-baqarah-286", "al-balad-4"]


@pytest.mark.asyncio
async def test_retrieval_oversamples_children_for_parent_coverage():
    repo = MultiResultRepository([retrieval_result("al-baqarah-286", 0.91)])

    await QuranRetriever(FakeEmbeddings(), repo, candidate_k=3, parent_k=4).search(
        "aku sedang berat"
    )

    assert repo.requested_top_k == 16
