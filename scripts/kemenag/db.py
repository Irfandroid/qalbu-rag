"""Paged reads and batched writes against the local corpus tables."""

from typing import Any

import asyncpg

from app.database.queries import vector_literal
from scripts.kemenag.config import CHUNK_UPSERT_BATCH_SIZE, DOCUMENT_UPSERT_BATCH_SIZE

_TABLES = ("quran_chunks", "quran_documents")

_DOCUMENT_SQL = """
insert into public.quran_documents
  (id, surah_number, surah_name, ayah_start, ayah_end, arabic_text,
   translation, tafsir, themes, source, metadata, corpus)
values ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
on conflict (id) do update set
  surah_number = excluded.surah_number,
  surah_name = excluded.surah_name,
  ayah_start = excluded.ayah_start,
  ayah_end = excluded.ayah_end,
  arabic_text = excluded.arabic_text,
  translation = excluded.translation,
  tafsir = excluded.tafsir,
  themes = excluded.themes,
  source = excluded.source,
  metadata = excluded.metadata,
  corpus = excluded.corpus,
  updated_at = now()
"""

_CHUNK_SQL = """
insert into public.quran_chunks
  (id, parent_id, chunk_type, content, embedding, metadata, corpus,
   embedding_provider, embedding_model, embedding_version,
   embedding_dimensions, embedding_fingerprint)
values ($1, $2, $3, $4, $5::vector, $6, $7, $8, $9, $10, $11, $12)
on conflict (id) do update set
  parent_id = excluded.parent_id,
  chunk_type = excluded.chunk_type,
  content = excluded.content,
  embedding = excluded.embedding,
  metadata = excluded.metadata,
  corpus = excluded.corpus,
  embedding_provider = excluded.embedding_provider,
  embedding_model = excluded.embedding_model,
  embedding_version = excluded.embedding_version,
  embedding_dimensions = excluded.embedding_dimensions,
  embedding_fingerprint = excluded.embedding_fingerprint
"""


async def corpus_rows(
    pool: asyncpg.Pool, table: str, corpus: str, columns: str = "*"
) -> list[dict[str, Any]]:
    """Read every row of one corpus table for the given corpus."""
    if table not in _TABLES:
        raise ValueError(f"Unsupported corpus table: {table}")
    rows = await pool.fetch(
        f"select {columns} from public.{table} where corpus = $1", corpus
    )
    return [dict(row) for row in rows]


async def upsert_documents(pool: asyncpg.Pool, documents: list[dict[str, Any]]) -> None:
    for start in range(0, len(documents), DOCUMENT_UPSERT_BATCH_SIZE):
        batch = documents[start : start + DOCUMENT_UPSERT_BATCH_SIZE]
        await pool.executemany(
            _DOCUMENT_SQL,
            [
                (
                    document["id"],
                    document["surah_number"],
                    document["surah_name"],
                    document["ayah_start"],
                    document["ayah_end"],
                    document.get("arabic_text"),
                    document.get("translation"),
                    document.get("tafsir"),
                    document.get("themes") or [],
                    document["source"],
                    document.get("metadata") or {},
                    document["corpus"],
                )
                for document in batch
            ],
        )


async def upsert_chunks(pool: asyncpg.Pool, chunks: list[dict[str, Any]]) -> None:
    for start in range(0, len(chunks), CHUNK_UPSERT_BATCH_SIZE):
        batch = chunks[start : start + CHUNK_UPSERT_BATCH_SIZE]
        await pool.executemany(
            _CHUNK_SQL,
            [
                (
                    chunk["id"],
                    chunk["parent_id"],
                    chunk["chunk_type"],
                    chunk["content"],
                    vector_literal(chunk["embedding"]),
                    chunk.get("metadata") or {},
                    chunk["corpus"],
                    chunk.get("embedding_provider"),
                    chunk.get("embedding_model"),
                    chunk.get("embedding_version"),
                    chunk.get("embedding_dimensions"),
                    chunk.get("embedding_fingerprint"),
                )
                for chunk in batch
            ],
        )


async def delete_rows(
    pool: asyncpg.Pool, table: str, corpus: str, ids: set[str]
) -> None:
    if table not in _TABLES:
        raise ValueError(f"Unsupported corpus table: {table}")
    if not ids:
        return
    await pool.execute(
        f"delete from public.{table} where corpus = $1 and id = any($2::text[])",
        corpus,
        sorted(ids),
    )
