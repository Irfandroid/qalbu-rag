"""Mental-health category manifest helpers shared by the corpus scripts."""

import json
import re
from pathlib import Path
from typing import Any, cast

from scripts.kemenag.config import ROOT

CATEGORY_MANIFEST = ROOT / "data/manifests/mental_health_categories.json"


def load_category_manifest(path: Path = CATEGORY_MANIFEST) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def category_index(
    manifest: dict[str, Any],
) -> tuple[dict[str, list[str]], list[str]]:
    """Map verse keys to category ids, plus categories with no configured keys."""
    by_verse: dict[str, list[str]] = {}
    pending: list[str] = []
    for category in manifest["categories"]:
        if category.get("guardrail_only"):
            continue
        keys = category.get("verse_keys", [])
        if not keys:
            pending.append(category["id"])
        for key in keys:
            by_verse.setdefault(key, []).append(category["id"])
    return by_verse, pending


def parent_categories(
    chunks: list[dict[str, Any]], by_verse: dict[str, list[str]]
) -> dict[str, list[str]]:
    """Collect sorted categories per parent id from chunk verse-key metadata."""
    result: dict[str, set[str]] = {}
    for chunk in chunks:
        verse_keys = str(chunk.get("metadata", {}).get("verse_key", "")).split(",")
        for verse_key in (key.strip() for key in verse_keys):
            for category in by_verse.get(verse_key, []):
                result.setdefault(chunk["parent_id"], set()).add(category)
    return {parent_id: sorted(categories) for parent_id, categories in result.items()}


def labelled_content(content: str, categories: list[str]) -> str:
    clean = re.sub(
        r"\nKategori (?:kesehatan mental|refleksi):.*$", "", content, flags=re.DOTALL
    )
    return (
        f"{clean}\n\nKategori kesehatan mental: "
        f"{', '.join(categories) or 'belum dipetakan'}"
    )
