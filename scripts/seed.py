import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings
from app.database.supabase import get_supabase
from app.quran.providers.catalog import get_active_documents

UPSERT_BATCH_SIZE = 100


async def main() -> None:
    client = await get_supabase(get_settings())
    documents = await get_active_documents()
    rows = [document.model_dump() for document in documents]
    for offset in range(0, len(rows), UPSERT_BATCH_SIZE):
        batch = rows[offset : offset + UPSERT_BATCH_SIZE]
        await client.table("quran_documents").upsert(batch).execute()
        print(f"Seeded {min(offset + len(batch), len(rows))}/{len(rows)} parents.")
    print(f"Seeded {len(rows)} parent documents.")


if __name__ == "__main__":
    asyncio.run(main())
