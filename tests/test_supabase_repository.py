import pytest

from app.database.queries import SupabaseQuranRepository


class Result:
    def __init__(self, data):
        self.data = data


class Request:
    def __init__(self, data):
        self.data = data

    def select(self, *_args):
        return self

    def in_(self, *_args):
        return self

    def eq(self, *_args):
        return self

    async def execute(self):
        return Result(self.data)


class Client:
    def rpc(self, name, params):
        assert name == "match_quran_chunks"
        assert params["match_count"] == 5
        assert params["corpus_filter"] == "qalbu-seed-v1"
        return Request(
            [
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
        )

@pytest.mark.asyncio
async def test_supabase_repository_maps_rpc():
    repository = SupabaseQuranRepository(Client(), "qalbu-seed-v1")
    results = await repository.match_chunks([0.1, 0.2], 5)
    assert results[0].parent_id == "parent-1"
