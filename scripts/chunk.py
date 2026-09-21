import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.quran.providers.catalog import get_active_documents
from app.rag.chunking import make_chunks


async def main() -> None:
    chunks = [
        chunk.model_dump()
        for document in await get_active_documents()
        for chunk in make_chunks(document)
    ]
    target = Path("data/temporary/chunks.json")
    target.write_text(json.dumps(chunks, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(chunks)} children to {target}.")


if __name__ == "__main__":
    asyncio.run(main())
