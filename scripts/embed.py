import asyncio
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings
from app.database.supabase import get_supabase
from app.rag.embeddings import LocalE5EmbeddingProvider, embedding_fingerprint

# Keep HNSW insert transactions below Supabase's statement timeout.
UPSERT_BATCH_SIZE = 32
EXISTING_PAGE_SIZE = 1000
UPLOAD_RETRIES = 5


async def upsert_with_retry(client, rows: list[dict]) -> None:
    """Retry transient PostgREST/database timeouts without re-embedding prior batches."""
    for attempt in range(1, UPLOAD_RETRIES + 1):
        try:
            await client.table("quran_chunks").upsert(rows).execute()
            return
        except Exception:
            if attempt == UPLOAD_RETRIES:
                raise
            delay = 2 ** (attempt - 1)
            print(f"Chunk upload failed; retrying in {delay}s ({attempt}/{UPLOAD_RETRIES}).")
            await asyncio.sleep(delay)


def priority_parent_ids() -> set[str]:
    """Prioritize the user's curated reflection references during a long first index."""
    references_path = Path("data/temporary/mental_health_references.csv")
    if not references_path.exists():
        return set()
    ids: set[str] = set()
    with references_path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            for ayah in range(int(row["ayah_start"]), int(row["ayah_end"]) + 1):
                ids.add(f"quran-com-en-{int(row['surah_number']):03d}-{ayah:03d}")
    return ids


async def existing_chunk_fingerprints(client) -> dict[str, str | None]:
    """Load manifests so only stale or missing vectors are embedded."""
    fingerprints: dict[str, str | None] = {}
    offset = 0
    while True:
        result = (
            await client.table("quran_chunks")
            .select("id,embedding_fingerprint")
            .order("id")
            .range(offset, offset + EXISTING_PAGE_SIZE - 1)
            .execute()
        )
        rows = result.data or []
        fingerprints.update(
            {row["id"]: row.get("embedding_fingerprint") for row in rows}
        )
        if len(rows) < EXISTING_PAGE_SIZE:
            return fingerprints
        offset += EXISTING_PAGE_SIZE


async def main() -> None:
    settings = get_settings()
    path = Path("data/temporary/chunks.json")
    if not path.exists():
        raise FileNotFoundError("Run `python scripts/chunk.py` first.")
    chunks = json.loads(path.read_text(encoding="utf-8"))
    provider = LocalE5EmbeddingProvider(settings.embedding_model, settings.embedding_dimensions)
    client = await get_supabase(settings)
    existing_fingerprints = await existing_chunk_fingerprints(client)
    fingerprints = {
        chunk["id"]: embedding_fingerprint(
            settings.embedding_model, settings.embedding_dimensions, chunk["content"]
        )
        for chunk in chunks
    }
    pending = [
        chunk
        for chunk in chunks
        if existing_fingerprints.get(chunk["id"]) != fingerprints[chunk["id"]]
    ]
    priority_ids = priority_parent_ids()
    pending.sort(key=lambda chunk: (chunk["parent_id"] not in priority_ids, chunk["id"]))
    print(f"Skipping {len(chunks) - len(pending)} current children.")
    prioritized_count = sum(chunk["parent_id"] in priority_ids for chunk in pending)
    print(f"Prioritizing {prioritized_count} curated children.")
    for offset in range(0, len(pending), UPSERT_BATCH_SIZE):
        batch = pending[offset : offset + UPSERT_BATCH_SIZE]
        vectors = provider.embed_documents([item["content"] for item in batch])
        rows = []
        for chunk, vector in zip(batch, vectors, strict=True):
            rows.append(
                {
                    **chunk,
                    "embedding": vector,
                    "embedding_fingerprint": fingerprints[chunk["id"]],
                    "embedding_model": settings.embedding_model,
                    "embedding_dimensions": settings.embedding_dimensions,
                }
            )
        await upsert_with_retry(client, rows)
        print(f"Embedded {min(offset + len(batch), len(pending))}/{len(pending)} pending children.")
    print(f"Embedding complete. Total corpus children: {len(chunks)}.")


if __name__ == "__main__":
    asyncio.run(main())
