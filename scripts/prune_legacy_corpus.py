"""Remove superseded parents only after complete replacement corpus is embedded."""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings
from app.database.supabase import get_supabase

PAGE_SIZE = 1000
DELETE_BATCH_SIZE = 100
ACTIVE_PREFIX = "quran-com-en-"
EXPECTED_PARENTS = 6236


async def ids_for_table(client, table: str) -> list[str]:
    ids: list[str] = []
    offset = 0
    while True:
        result = (
            await client.table(table).select("id").range(offset, offset + PAGE_SIZE - 1).execute()
        )
        rows = result.data or []
        ids.extend(row["id"] for row in rows)
        if len(rows) < PAGE_SIZE:
            return ids
        offset += PAGE_SIZE


async def main() -> None:
    chunks_path = Path("data/temporary/chunks.json")
    if not chunks_path.exists():
        raise FileNotFoundError("Run `python scripts/chunk.py` first.")
    local_chunks = json.loads(chunks_path.read_text(encoding="utf-8"))
    expected_child_ids = {item["id"] for item in local_chunks}

    client = await get_supabase(get_settings())
    parent_ids = await ids_for_table(client, "quran_documents")
    child_ids = await ids_for_table(client, "quran_chunks")
    active_parents = {item for item in parent_ids if item.startswith(ACTIVE_PREFIX)}
    active_children = {item for item in child_ids if item in expected_child_ids}
    if len(active_parents) != EXPECTED_PARENTS:
        raise RuntimeError(
            "Refusing prune: expected "
            f"{EXPECTED_PARENTS} active parents, found {len(active_parents)}"
        )
    if active_children != expected_child_ids:
        raise RuntimeError(
            "Refusing prune: embedded "
            f"{len(active_children)}/{len(expected_child_ids)} active children"
        )

    legacy_ids = [item for item in parent_ids if not item.startswith(ACTIVE_PREFIX)]
    for offset in range(0, len(legacy_ids), DELETE_BATCH_SIZE):
        batch = legacy_ids[offset : offset + DELETE_BATCH_SIZE]
        await client.table("quran_documents").delete().in_("id", batch).execute()
        print(
            f"Removed {min(offset + len(batch), len(legacy_ids))}/{len(legacy_ids)} legacy parents."
        )
    print(f"Prune complete. Active parents={len(active_parents)}, children={len(active_children)}.")


if __name__ == "__main__":
    asyncio.run(main())
