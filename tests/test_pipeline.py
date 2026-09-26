import pytest

from app.models.chat import QalbuResponse, QuranReference
from app.models.quran import QuranDocument
from app.models.rag import RetrievalResult
from app.rag.citation_validator import CitationValidator
from app.rag.pipeline import QalbuRAG
from app.safety.guardrails import SafetyGuardrails, SafetyLevel

SOURCE_ID = "qalbu-seed-013-028"


def source() -> QuranDocument:
    return QuranDocument(
        id=SOURCE_ID,
        surah_number=13,
        surah_name="Ar-Ra'd",
        ayah_start=28,
        ayah_end=28,
        translation="Hanya dengan mengingat Allah hati menjadi tenteram.",
        tafsir="Tafsir menjelaskan zikir sebagai tasbih, tahmid, dan membaca Al-Qur'an.",
        source={"quran": "Kemenag"},
    )


class Repository:
    def __init__(self) -> None:
        self.document = source()

    async def get_documents(self, identifiers: list[str]) -> list[QuranDocument]:
        return [self.document for identifier in identifiers if identifier == SOURCE_ID]


class VectorRetriever:
    parent_k = 3

    def __init__(self, repository: Repository) -> None:
        self.repository = repository

    async def search(
        self, query: str, request_id: str | None = None
    ) -> list[RetrievalResult]:
        return [
            RetrievalResult(
                child_id="child:13:28",
                parent_id=SOURCE_ID,
                score=0.9,
                chunk_type="ayah",
                surah_number=13,
                surah_name="Ar-Ra'd",
                ayah_start=28,
                ayah_end=28,
            )
        ]


class SequenceLLM:
    def __init__(self, responses: list[QalbuResponse]) -> None:
        self.responses = responses
        self.calls = 0

    async def generate(self, query: str, context: str, max_tokens: int = 120):
        response = self.responses[self.calls]
        self.calls += 1
        return response


class FailingLLM:
    async def generate(self, query: str, context: str, max_tokens: int = 120):
        raise RuntimeError("provider down")


class ExplodingRetriever:
    parent_k = 3

    async def search(self, query: str, request_id: str | None = None):
        raise AssertionError("out-of-scope query must not call external retrieval")


def build_rag(retriever, llm) -> QalbuRAG:
    return QalbuRAG(
        SafetyGuardrails(),
        retriever,
        llm,
        CitationValidator(),
    )


@pytest.mark.asyncio
async def test_retrieval_returns_vector_parents():
    repository = Repository()
    rag = build_rag(VectorRetriever(repository), FailingLLM())

    results, documents = await rag.retrieve("Aku bingung dengan tujuan hidup", "test")

    assert results[0].parent_id == SOURCE_ID
    assert [document.id for document in documents] == [SOURCE_ID]


@pytest.mark.asyncio
async def test_generation_retries_once_when_first_draft_ignores_context():
    reference = [QuranReference(parent_id=SOURCE_ID)]
    llm = SequenceLLM(
        [
            QalbuResponse(answer="Jawaban umum.", references=reference),
            QalbuResponse(
                answer=(
                    "Rasa cemas bisa terasa berat. Ayat ini mengajak hati mencari ketenteraman. "
                    "Dalam tafsir yang tersedia, zikir mencakup tasbih dan tahmid."
                ),
                references=reference,
            ),
        ]
    )
    rag = build_rag(VectorRetriever(Repository()), llm)

    response = await rag._generate_validated(
        user_query="Aku merasa cemas",
        generation_query="Pesan pengguna: Aku merasa cemas",
        documents=[source()],
        max_tokens=72,
        request_id="test",
    )

    assert response is not None
    assert "cemas" in response.answer
    assert llm.calls == 2


@pytest.mark.asyncio
async def test_generator_failure_returns_retrieved_sources():
    rag = build_rag(VectorRetriever(Repository()), FailingLLM())

    response = await rag.ask("Aku merasa hidup berat", "test-fallback")

    assert "Refleksi AI sedang tidak tersedia" in response.answer
    assert response.references[0].parent_id == SOURCE_ID
    assert response.evidence


@pytest.mark.asyncio
async def test_out_of_scope_query_is_rejected_before_external_retrieval():
    rag = build_rag(ExplodingRetriever(), FailingLLM())  # type: ignore[arg-type]

    response = await rag.ask("Berapa harga Bitcoin besok?", "test-scope")

    assert "di luar ruang refleksi" in response.answer
    assert response.references == []


def test_high_distress_adds_human_support_note():
    response = QalbuRAG._with_distress_note(
        QalbuResponse(answer="Refleksi", references=[]),
        SafetyLevel.HIGH_DISTRESS,
    )
    assert "orang tepercaya" in (response.safety_note or "")
