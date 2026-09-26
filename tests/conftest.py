from app.models.quran import QuranDocument
from app.models.rag import RetrievalResult


def document() -> QuranDocument:
    return QuranDocument(
        id="al-baqarah-286",
        surah_number=2,
        surah_name="Al-Baqarah",
        ayah_start=286,
        ayah_end=286,
        themes=["capacity", "burden"],
        source={"quran": "[TEMPORARY SOURCE]"},
        metadata={"temporary": True},
    )


class FakeEmbeddings:
    async def embed_query(self, text: str) -> list[float]:
        return [0.1, 0.2]

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[0.1, 0.2] for _ in texts]


class FakeRepository:
    async def match_chunks(self, embedding: list[float], top_k: int) -> list[RetrievalResult]:
        return [
            RetrievalResult(
                child_id="al-baqarah-286:themes",
                parent_id="al-baqarah-286",
                score=0.9,
                chunk_type="themes",
                surah_number=2,
                surah_name="Al-Baqarah",
                ayah_start=286,
                ayah_end=286,
            )
        ]

    async def get_documents(self, ids: list[str]) -> list[QuranDocument]:
        return [document() for _ in ids]
