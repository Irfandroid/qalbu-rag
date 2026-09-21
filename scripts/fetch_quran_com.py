"""Snapshot complete Quran.com Arabic text and Saheeh International translation."""

import asyncio
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BASE_URL = "https://api.quran.com/api/v4"
TRANSLATION_RESOURCE_ID = 20
TARGET = Path("data/external/quran-com/saheeh-international.json")


async def fetch_json(client: httpx.AsyncClient, path: str) -> dict:
    response = await client.get(f"{BASE_URL}/{path}")
    response.raise_for_status()
    return response.json()


async def main() -> None:
    async with httpx.AsyncClient(timeout=90, follow_redirects=True) as client:
        chapters, arabic, translation = await asyncio.gather(
            fetch_json(client, "chapters?language=en"),
            fetch_json(client, "quran/verses/uthmani"),
            fetch_json(
                client,
                (
                    f"quran/translations/{TRANSLATION_RESOURCE_ID}"
                    "?fields=verse_key,chapter_id,verse_number,resource_name,language_name"
                ),
            ),
        )

    verses = arabic.get("verses", [])
    translations = translation.get("translations", [])
    if len(verses) != 6236 or len(translations) != 6236:
        raise RuntimeError(
            f"Incomplete Quran.com snapshot: arabic={len(verses)}, translations={len(translations)}"
        )
    by_key = {item["verse_key"]: item for item in translations}
    if set(by_key) != {item["verse_key"] for item in verses}:
        raise RuntimeError("Arabic and translation verse keys do not match")

    payload = {
        "source": {
            "provider": "Quran.com legacy Content API v4",
            "base_url": BASE_URL,
            "translation_resource_id": TRANSLATION_RESOURCE_ID,
            "translation_name": translation.get("meta", {}).get("translation_name"),
            "translation_author": translation.get("meta", {}).get("author_name"),
            "fetched_at": datetime.now(UTC).isoformat(),
        },
        "chapters": chapters["chapters"],
        "verses": [
            {
                "verse_key": item["verse_key"],
                "text_uthmani": item["text_uthmani"].strip(),
                "translation": by_key[item["verse_key"]]["text"].strip(),
            }
            for item in verses
        ],
    }
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
    payload["source"]["content_sha256"] = hashlib.sha256(encoded).hexdigest()
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"Saved {len(payload['verses'])} verses and {len(payload['chapters'])} chapters "
        f"to {TARGET}."
    )


if __name__ == "__main__":
    asyncio.run(main())
