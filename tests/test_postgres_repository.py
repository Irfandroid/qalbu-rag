import pytest

from app.database.queries import PostgresQuranRepository, vector_literal


class Pool:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    async def fetch(self, sql: str, *args: object) -> list[dict]:
        self.calls.append((sql, args))
        if "match_quran_chunks" in sql:
            return [
                {
                    "child_id": "child-1",
                    "parent_id": "parent-1",
                    "score": 0.81,
                    "chunk_type": "translation",
                    "surah_number": 13,
                    "surah_name": "Ar-Ra'd",
                    "ayah_start": 28,
                    "ayah_end": 28,
                }
            ]
        return [
            {
                "id": "parent-1",
                "surah_number": 13,
                "surah_name": "Ar-Ra'd",
                "ayah_start": 28,
                "ayah_end": 28,
                "arabic_text": "عربي",
                "translation": "terjemahan",
                "tafsir": None,
                "themes": [],
                "source": {"quran": "Quran Kemenag"},
                "metadata": {"source_provider": "official_portal"},
            }
        ]


@pytest.mark.asyncio
async def test_repository_maps_vector_search_rows():
    pool = Pool()
    repository = PostgresQuranRepository(pool, "qalbu-seed-v1")  # type: ignore[arg-type]
    results = await repository.match_chunks([0.1, 0.2], 5)
    assert results[0].parent_id == "parent-1"
    assert pool.calls[0][1] == ("[0.1,0.2]", 5, "qalbu-seed-v1")


@pytest.mark.asyncio
async def test_repository_preserves_requested_document_order():
    pool = Pool()
    repository = PostgresQuranRepository(pool, "qalbu-seed-v1")  # type: ignore[arg-type]
    documents = await repository.get_documents(["parent-1", "missing"])
    assert [document.id for document in documents] == ["parent-1"]


def test_vector_literal_is_pgvector_text_format():
    assert vector_literal([0.5, -0.25]) == "[0.5,-0.25]"
