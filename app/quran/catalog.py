"""Canonical metadata for the public Quran dataset catalog."""

import json
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, cast
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
CORPUS = "qalbu-kemenag-v1"
CHUNK_TYPES = ("arabic", "translation", "tafsir", "themes")
MANIFEST_PATH = ROOT / "data/manifests/kemenag_corpus_verses.json"
REFLECTION_MANIFEST_PATH = ROOT / "data/manifests/kemenag_reflection_verses.json"
CATEGORY_MANIFEST_PATH = ROOT / "data/manifests/mental_health_categories.json"
DAILY_TIMEZONE = ZoneInfo("Asia/Jakarta")
DAILY_VERSE_EPOCH = date(2026, 1, 1)


def expand_ranges(ranges: list[str]) -> list[str]:
    keys: list[str] = []
    for item in ranges:
        surah, ayahs = item.split(":", 1)
        bounds = [int(value) for value in ayahs.split("-", 1)]
        keys.extend(f"{int(surah)}:{ayah}" for ayah in range(bounds[0], bounds[-1] + 1))
    return list(dict.fromkeys(keys))


def parent_id(corpus: str, verse_key: str) -> str:
    surah, ayah = (int(part) for part in verse_key.split(":", 1))
    return f"{corpus}-{surah:03d}-{ayah:03d}"


def child_id(parent: str, chunk_type: str) -> str:
    if chunk_type not in CHUNK_TYPES:
        raise ValueError(f"Unsupported Quran chunk type: {chunk_type}")
    return f"{parent}:{chunk_type}"


def daily_date_in_timezone(moment: datetime | None = None) -> date:
    """Return current product date, consistently using Asia/Jakarta."""
    current = moment or datetime.now(DAILY_TIMEZONE)
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)
    return current.astimezone(DAILY_TIMEZONE).date()


def select_verse_of_day(verse_keys: list[str], day: date) -> str:
    """Select one stable verse from a sorted, deduplicated corpus inventory."""
    keys = sorted(
        set(verse_keys),
        key=lambda value: tuple(int(part) for part in value.split(":", 1)),
    )
    if not keys:
        raise ValueError("Cannot select a daily verse from an empty corpus")
    offset = (day - DAILY_VERSE_EPOCH).days % len(keys)
    return keys[offset]


def load_json(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def category_index() -> tuple[dict[str, list[str]], dict[str, str]]:
    by_verse: dict[str, list[str]] = {}
    labels: dict[str, str] = {}
    for category in load_json(CATEGORY_MANIFEST_PATH)["categories"]:
        if category.get("guardrail_only"):
            continue
        category_id = category["id"]
        labels[category_id] = category.get("label", category_id)
        for verse_key in category.get("verse_keys", []):
            by_verse.setdefault(verse_key, []).append(category_id)
    return by_verse, labels


def build_catalog(child_counts: dict[str, int] | None = None) -> dict[str, Any]:
    manifest = load_json(MANIFEST_PATH)
    reflection = load_json(REFLECTION_MANIFEST_PATH)
    categories, labels = category_index()
    keys = sorted(
        expand_ranges(manifest["ranges"]),
        key=lambda value: tuple(int(part) for part in value.split(":", 1)),
    )
    reflection_keys = set(expand_ranges(reflection["ranges"]))
    verses = []
    for key in keys:
        surah, ayah = (int(part) for part in key.split(":", 1))
        category_ids = sorted(categories.get(key, []))
        verses.append(
            {
                "verse_key": key,
                "surah_number": surah,
                "surah_name": manifest["surah_names"].get(str(surah), f"Surah {surah}"),
                "ayah_number": ayah,
                "categories": [
                    {"id": category_id, "label": labels[category_id]}
                    for category_id in category_ids
                ],
                "in_reflection_subset": key in reflection_keys,
            }
        )
    counts = manifest.get("counts", {})
    if child_counts is not None:
        actual_child_counts = child_counts
    else:
        actual_child_counts = counts.get("child_counts") or {
            chunk_type: len(verses) for chunk_type in CHUNK_TYPES
        }
    return {
        "version": manifest["version"],
        "corpus": manifest["corpus"],
        "status": manifest.get("status", "verified"),
        "verified_at": manifest.get("verified_at"),
        "source": manifest["source"],
        "parent_count": len(verses),
        "child_counts": {
            chunk_type: actual_child_counts.get(chunk_type, 0)
            for chunk_type in CHUNK_TYPES
        },
        "reflection_subset": len(reflection_keys),
        "category_options": [
            {"id": category_id, "label": label}
            for category_id, label in sorted(labels.items(), key=lambda item: item[1])
        ],
        "verses": verses,
    }
