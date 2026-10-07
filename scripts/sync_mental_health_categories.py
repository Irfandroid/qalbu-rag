"""Attach the verified Kemenag snapshot to the mental-health taxonomy."""

import argparse
import asyncio
import json
import re
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.providers.embeddings.jina import JinaEmbeddingProvider, embedding_fingerprint
from supabase import acreate_client

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/manifests/mental_health_categories.json"
LOCAL_CHILDREN = ROOT / "data/processed/kemenag_portal_seed_children.json"


def load_manifest() -> dict[str, Any]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def category_index(manifest: dict[str, Any]) -> tuple[dict[str, list[str]], list[str]]:
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
    result: dict[str, set[str]] = {}
    for chunk in chunks:
        verse_keys = str(chunk.get("metadata", {}).get("verse_key", "")).split(",")
        for verse_key in (key.strip() for key in verse_keys):
            for category in by_verse.get(verse_key, []):
                result.setdefault(chunk["parent_id"], set()).add(category)
    return {parent_id: sorted(categories) for parent_id, categories in result.items()}


def labelled_content(content: str, categories: list[str]) -> str:
    clean = re.sub(r"\n\nKategori kesehatan mental:.*$", "", content, flags=re.DOTALL)
    return f"{clean}\n\nKategori kesehatan mental: {', '.join(categories)}"


def local_dry_run(manifest: dict[str, Any]) -> None:
    children = json.loads(LOCAL_CHILDREN.read_text(encoding="utf-8"))
    by_verse, pending = category_index(manifest)
    mapped = {
        key
        for key in by_verse
        if any(c.get("metadata", {}).get("verse_key") == key for c in children)
    }
    print(f"Kemenag snapshot: {len(children)} ayat, {len(mapped)} mapped verse keys")
    print(f"Categories ready: {len({category for key in mapped for category in by_verse[key]})}")
    print(f"Categories pending API fetch: {', '.join(pending) or 'none'}")


async def sync() -> None:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_server_key or not settings.jina_api_key:
        raise RuntimeError("SUPABASE_URL, Supabase server key, and JINA_API_KEY are required")

    manifest = load_manifest()
    by_verse, pending = category_index(manifest)
    client = await acreate_client(settings.supabase_url, settings.supabase_server_key)
    documents = (
            await client.table("quran_documents")
            .select("*")
            .eq("corpus", manifest["corpus"])
            .execute()
        ).data
    chunks = (
            await client.table("quran_chunks")
            .select("*")
            .eq("corpus", manifest["corpus"])
            .execute()
        ).data
    if any(
        (document.get("metadata") or {}).get("source_provider") != "official_portal"
        or "kementerian agama" not in str(
            (document.get("metadata") or {}).get("source_authority", "")
        ).casefold()
        for document in documents
    ):
        raise RuntimeError("Active corpus contains a non-Kemenag source; refusing to relabel it")

    grouped = parent_categories(chunks, by_verse)
    available_keys = {
        key.strip()
        for chunk in chunks
        for key in str(chunk.get("metadata", {}).get("verse_key", "")).split(",")
    }
    missing_keys = sorted(key for key in by_verse if key not in available_keys)
    changed_documents = 0
    for document in documents:
        categories = grouped.get(document["id"], [])
        if not categories:
            continue
        themes = sorted(set(document.get("themes") or []) | set(categories))
        metadata = dict(document.get("metadata") or {})
        metadata.update(
            {
                "mental_health_categories": categories,
                "category_manifest_version": manifest["version"],
            }
        )
        if themes != document.get("themes") or metadata != document.get("metadata"):
            await client.table("quran_documents").update(
                {"themes": themes, "metadata": metadata}
            ).eq("id", document["id"]).execute()
            changed_documents += 1

    to_embed: list[tuple[dict[str, Any], str, dict[str, Any]]] = []
    for chunk in chunks:
        categories = grouped.get(chunk["parent_id"], [])
        if not categories:
            continue
        content = labelled_content(chunk["content"], categories)
        metadata = dict(chunk.get("metadata") or {})
        metadata.update(
            {
                "mental_health_categories": categories,
                "category_manifest_version": manifest["version"],
            }
        )
        if content != chunk["content"] or metadata != chunk.get("metadata"):
            to_embed.append((chunk, content, metadata))

    embeddings = []
    provider = JinaEmbeddingProvider(
        settings.jina_api_key,
        settings.jina_embedding_model,
        settings.embedding_dimensions,
        settings.request_timeout_seconds,
    )
    for start in range(0, len(to_embed), 16):
        batch = [item[1] for item in to_embed[start : start + 16]]
        embeddings.extend(await provider.embed_documents(batch))

    for (chunk, content, metadata), vector in zip(to_embed, embeddings, strict=True):
        await client.table("quran_chunks").update(
            {
                "content": content,
                "metadata": metadata,
                "embedding": vector,
                "embedding_provider": "jina",
                "embedding_model": settings.jina_embedding_model,
                "embedding_version": manifest["version"],
                "embedding_dimensions": settings.embedding_dimensions,
                "embedding_fingerprint": embedding_fingerprint(
                    settings.jina_embedding_model, settings.embedding_dimensions, content
                ),
            }
        ).eq("id", chunk["id"]).execute()
    print(f"Updated documents: {changed_documents}; re-embedded chunks: {len(to_embed)}")
    print(f"Verse keys pending API fetch: {', '.join(missing_keys) or 'none'}")
    print(f"Categories with no configured keys: {', '.join(pending) or 'none'}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run", action="store_true", help="validate the local Kemenag snapshot only"
    )
    args = parser.parse_args()
    if args.dry_run:
        local_dry_run(load_manifest())
    else:
        asyncio.run(sync())


if __name__ == "__main__":
    main()
