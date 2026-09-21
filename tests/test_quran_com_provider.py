import pytest

from app.quran.providers.quran_com_english import QuranComEnglishProvider
from app.rag.chunking import make_chunks


@pytest.mark.asyncio
async def test_quran_com_snapshot_is_complete_and_attributed():
    documents = await QuranComEnglishProvider().get_documents()
    assert len(documents) == 6236
    assert documents[0].id == "quran-com-en-001-001"
    assert documents[-1].id == "quran-com-en-114-006"
    assert documents[0].translation
    assert documents[0].metadata["translation_name"] == "Saheeh International"
    assert {document.surah_number for document in documents} == set(range(1, 115))


@pytest.mark.asyncio
async def test_child_search_chunks_map_back_to_complete_parent():
    document = (await QuranComEnglishProvider().get_documents())[0]
    chunks = make_chunks(document)
    assert chunks
    assert all(chunk.parent_id == document.id for chunk in chunks)
    assert "translation" in {chunk.chunk_type for chunk in chunks}
    assert "arabic" not in {chunk.chunk_type for chunk in chunks}
