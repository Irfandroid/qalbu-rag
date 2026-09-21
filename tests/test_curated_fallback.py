import pytest

from app.models.quran import QuranDocument
from app.rag.curated_fallback import CuratedFallbackRetriever


class FakeRepository:
    def __init__(self, documents: list[QuranDocument]) -> None:
        self.documents = {document.id: document for document in documents}

    async def get_documents(self, ids: list[str]) -> list[QuranDocument]:
        return [self.documents[item_id] for item_id in ids if item_id in self.documents]


def document(id: str) -> QuranDocument:
    return QuranDocument(
        id=id,
        surah_number=23,
        surah_name="Al-Mu'minun",
        ayah_start=115,
        ayah_end=115,
        source={"quran": "Kaggle community mirror"},
    )


@pytest.mark.asyncio
async def test_purpose_intent_uses_stored_curated_parents():
    documents = [
        document("quran-com-en-023-115"),
        document("quran-com-en-051-056"),
    ]
    results = await CuratedFallbackRetriever(FakeRepository(documents)).search(
        "Aku bingung dengan tujuan hidup"
    )
    assert [item.id for item in results] == [item.id for item in documents]


@pytest.mark.asyncio
async def test_unknown_intent_has_no_fallback():
    assert not await CuratedFallbackRetriever(FakeRepository([])).search("harga Bitcoin hari ini")


@pytest.mark.asyncio
async def test_emptiness_intent_uses_reviewed_calm_parent_only():
    documents = [
        document("quran-com-en-013-028"),
    ]
    results = await CuratedFallbackRetriever(FakeRepository(documents)).search(
        "Aku merasa hampa dan kehilangan arah"
    )
    assert [item.id for item in results] == ["quran-com-en-013-028"]
