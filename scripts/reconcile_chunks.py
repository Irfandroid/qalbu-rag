"""Remove retired child chunks only after every current chunk is embedded."""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings
from app.database.supabase import get_supabase

PAGE_SIZE = 1000
DELETE_BATCH_SIZE = 100


async def remote_chunks(client) -> list[dict[str, str]]:
    """Read stable, paginated IDs so reconciliation cannot miss a page."""
    rows: list[dict[str, str]] = []
    offset = 0
    while True:
        result = (
            await client.table("quran_chunks")
            .select("id,parent_id")
            .order("id")
            .range(offset, offset + PAGE_SIZE - 1)
            .execute()
        )
        page = result.data or []
        rows.extend(page)
        if len(page) < PAGE_SIZE:
            return rows
        offset += PAGE_SIZE


async def main() -> None:
    chunks_path = Path("data/temporary/chunks.json")
    if not chunks_path.exists():
        raise FileNotFoundError("Run `python scripts/chunk.py` first.")
    expected = json.loads(chunks_path.read_text(encoding="utf-8"))
    expected_ids = {chunk["id"] for chunk in expected}
    active_parent_ids = {chunk["parent_id"] for chunk in expected}
    if not expected_ids or not active_parent_ids:
        raise RuntimeError("Refusing reconciliation: generated chunk manifest is empty.")

    client = await get_supabase(get_settings())
    remote = await remote_chunks(client)
    remote_current_ids = {
        row["id"] for row in remote if row["parent_id"] in active_parent_ids
    }
    missing = expected_ids - remote_current_ids
    if missing:
        raise RuntimeError(
            "Refusing reconciliation: run `python scripts/embed.py` first; "
            f"{len(missing)} expected child chunks are missing."
        )

    retired_ids = sorted(remote_current_ids - expected_ids)
    for offset in range(0, len(retired_ids), DELETE_BATCH_SIZE):
        batch = retired_ids[offset : offset + DELETE_BATCH_SIZE]
        await client.table("quran_chunks").delete().in_("id", batch).execute()
        removed = min(offset + len(batch), len(retired_ids))
        print(f"Removed {removed}/{len(retired_ids)} retired chunks.")
    print(
        "Reconciliation complete. "
        f"Current children={len(expected_ids)}, retired removed={len(retired_ids)}."
    )


if __name__ == "__main__":
    asyncio.run(main())
