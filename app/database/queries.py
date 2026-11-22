from collections.abc import Sequence
from typing import Any

import asyncpg

from app.models.quran import QuranDocument
from app.models.rag import RetrievalResult
from app.quran.catalog import CORPUS


def vector_literal(embedding: Sequence[float]) -> str:
    """pgvector accepts its text representation; asyncpg has no native codec."""
    return "[" + ",".join(f"{value:.8g}" for value in embedding) + "]"


class PostgresQuranRepository:
    def __init__(self, pool: asyncpg.Pool, corpus: str = CORPUS) -> None:
        self.pool = pool
        self.corpus = corpus

    async def match_chunks(self, embedding: list[float], top_k: int) -> list[RetrievalResult]:
        rows = await self.pool.fetch(
            """
            select child_id, parent_id, score::float8 as score, chunk_type,
                   surah_number, surah_name, ayah_start, ayah_end
            from public.match_quran_chunks($1::vector, $2, $3)
            """,
            vector_literal(embedding),
            top_k,
            self.corpus,
        )
        return [RetrievalResult.model_validate(dict(row)) for row in rows]

    async def get_documents(self, ids: list[str]) -> list[QuranDocument]:
        if not ids:
            return []
        rows = await self.pool.fetch(
            """
            select id, surah_number, surah_name, ayah_start, ayah_end,
                   arabic_text, translation, tafsir, themes, source, metadata
            from public.quran_documents
            where corpus = $1 and id = any($2::text[])
            """,
            self.corpus,
            ids,
        )
        by_id = {row["id"]: QuranDocument.model_validate(dict(row)) for row in rows}
        return [by_id[document_id] for document_id in ids if document_id in by_id]


async def chunk_type_counts(pool: asyncpg.Pool, corpus: str) -> dict[str, int]:
    rows: list[Any] = await pool.fetch(
        "select chunk_type from public.quran_chunks where corpus = $1", corpus
    )
    counts: dict[str, int] = {}
    for row in rows:
        chunk_type = row["chunk_type"]
        counts[chunk_type] = counts.get(chunk_type, 0) + 1
    return counts
