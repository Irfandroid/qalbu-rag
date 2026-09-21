"""Conservative fallback while vector indexing is incomplete.

It selects only explicitly curated, stored parents; it never manufactures Quran
content or a citation. Vector retrieval remains the normal path.
"""

from app.quran.repository import QuranRepository

CURATED_INTENTS: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (
        ("hampa", "jampa", "kosong", "kehilangan arah", "tidak bermakna", "tak bermakna"),
        # Keep one reviewed primary source. 51:56 discusses purpose, but the
        # smaller local model tended to ignore the user's emptiness and turn
        # the whole answer into a generic purpose statement.
        ("quran-com-en-013-028",),
    ),
    (
        ("tujuan hidup", "makna hidup", "arti hidup"),
        ("quran-com-en-023-115", "quran-com-en-051-056"),
    ),
    (
        ("cemas", "kecemasan", "gelisah", "takut"),
        ("quran-com-en-013-028", "quran-com-en-002-286"),
    ),
    (
        ("sedih", "putus asa", "harapan"),
        ("quran-com-en-012-086", "quran-com-en-012-087"),
    ),
    (
        ("ujian", "cobaan", "sulit", "kesulitan"),
        ("quran-com-en-029-002", "quran-com-en-002-214", "quran-com-en-094-005"),
    ),
    (
        ("berat", "beban", "lelah", "gagal"),
        ("quran-com-en-002-286", "quran-com-en-090-004"),
    ),
)


class CuratedFallbackRetriever:
    def __init__(self, repository: QuranRepository) -> None:
        self.repository = repository

    async def search(self, query: str):
        normalized = query.casefold()
        for keywords, parent_ids in CURATED_INTENTS:
            if any(keyword in normalized for keyword in keywords):
                return await self.repository.get_documents(list(parent_ids))
        return []
