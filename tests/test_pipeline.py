import pytest

from app.models.chat import QalbuResponse, QuranReference
from app.models.quran import QuranDocument
from app.models.rag import RetrievalResult
from app.rag.citation_validator import CitationValidator
from app.rag.pipeline import QalbuRAG
from app.safety.guardrails import SafetyGuardrails


def quran_document(identifier: str) -> QuranDocument:
    surah, ayah = {
        "quran-com-en-023-115": (23, 115),
        "quran-com-en-051-056": (51, 56),
        "quran-com-en-069-027": (69, 27),
    }[identifier]
    return QuranDocument(
        id=identifier,
        surah_number=surah,
        surah_name="Test",
        ayah_start=ayah,
        ayah_end=ayah,
        source={"quran": "Quran.com"},
    )


class Repository:
    def __init__(self) -> None:
        self.documents = {
            identifier: quran_document(identifier)
            for identifier in (
                "quran-com-en-023-115",
                "quran-com-en-051-056",
                "quran-com-en-069-027",
            )
        }

    async def get_documents(self, identifiers: list[str]) -> list[QuranDocument]:
        return [self.documents[identifier] for identifier in identifiers]


class VectorRetriever:
    parent_k = 3

    async def search(self, query: str) -> list[RetrievalResult]:
        return [
            RetrievalResult(
                child_id="quran-com-en-069-027:translation:000",
                parent_id="quran-com-en-069-027",
                score=0.9,
                chunk_type="translation",
                surah_number=69,
                surah_name="Al-Haqqah",
                ayah_start=27,
                ayah_end=27,
            )
        ]


class ParentRetriever:
    def __init__(self, repository: Repository) -> None:
        self.repository = repository

    async def get_parents(self, results: list[RetrievalResult]) -> list[QuranDocument]:
        return await self.repository.get_documents([result.parent_id for result in results])


class SequenceLLM:
    def __init__(self, responses: list[QalbuResponse]) -> None:
        self.responses = responses
        self.calls = 0

    async def generate(self, query: str, context: str, max_tokens: int = 120):
        response = self.responses[self.calls]
        self.calls += 1
        return response


@pytest.mark.asyncio
async def test_explicit_curated_intent_excludes_weaker_vector_parent_from_context():
    repository = Repository()
    rag = QalbuRAG(
        SafetyGuardrails(),
        VectorRetriever(),
        ParentRetriever(repository),
        llm=None,  # type: ignore[arg-type]
        validator=None,  # type: ignore[arg-type]
    )

    children, documents = await rag.retrieve("Aku bingung dengan tujuan hidup", "test")

    assert [child.parent_id for child in children] == ["quran-com-en-069-027"]
    assert [document.id for document in documents] == [
        "quran-com-en-023-115",
        "quran-com-en-051-056",
    ]


@pytest.mark.asyncio
async def test_generation_retries_once_when_first_draft_ignores_context():
    source = QuranDocument(
        id="test-anxiety-source",
        surah_number=13,
        surah_name="Ar-Ra'd",
        ayah_start=28,
        ayah_end=28,
        translation="Hearts are assured by remembrance of Allah.",
        tafsir="Tasbih and tahmid are forms of remembrance.",
        source={"quran": "Quran.com"},
    )
    reference = [QuranReference(parent_id=source.id)]
    llm = SequenceLLM(
        [
            QalbuResponse(answer="Jawaban umum.", references=reference),
            QalbuResponse(
                answer=(
                    "Rasa cemas bisa terasa berat. Ayat ini mengajak hati mengingat Allah. "
                    "Dalam tafsir yang tersedia, zikir mencakup tasbih dan tahmid."
                ),
                references=reference,
            ),
        ]
    )
    repository = Repository()
    rag = QalbuRAG(
        SafetyGuardrails(),
        VectorRetriever(),
        ParentRetriever(repository),
        llm=llm,
        validator=CitationValidator(),
    )

    response = await rag._generate_validated(
        user_query="Aku merasa cemas",
        generation_query="Current user message: Aku merasa cemas",
        documents=[source],
        max_tokens=72,
        request_id="test",
    )

    assert response is not None
    assert "cemas" in response.answer
    assert llm.calls == 2
