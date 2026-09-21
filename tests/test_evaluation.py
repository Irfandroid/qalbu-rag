from app.models.chat import QalbuResponse, QuranReference
from app.models.rag import RetrievalResult
from evaluation.evaluate import evaluate_case
from tests.conftest import document


def result(parent_id: str, score: float = 0.9) -> RetrievalResult:
    return RetrievalResult(
        child_id=f"{parent_id}:themes",
        parent_id=parent_id,
        score=score,
        chunk_type="themes",
        surah_number=2,
        surah_name="Al-Baqarah",
        ayah_start=286,
        ayah_end=286,
    )


def test_evaluation_accepts_exact_grounded_citation():
    response = QalbuResponse(
        answer="Refleksi singkat.",
        references=[
            QuranReference(
                parent_id="al-baqarah-286",
                surah_number=2,
                surah_name="Al-Baqarah",
                ayah_start=286,
                ayah_end=286,
            )
        ],
    )
    report = evaluate_case(
        {"query": "hidup berat", "expected_sources": ["al-baqarah-286"]},
        [result("al-baqarah-286")],
        [document()],
        response,
    )
    assert report["overall_score"] == 5


def test_evaluation_rejects_unsupported_query_that_answers_anyway():
    report = evaluate_case(
        {"query": "harga Bitcoin", "expected_mode": "refusal", "expected_sources": []},
        [result("al-baqarah-286")],
        [document()],
        QalbuResponse(answer="Bitcoin naik.", references=[]),
    )
    assert report["criteria"]["retrieval_quality"]["score"] == 2
    assert report["criteria"]["answer_relevance"]["score"] == 1
