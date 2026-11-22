"""Attach the verified Kemenag snapshot to the mental-health taxonomy."""

import argparse
import asyncio
import json
from typing import Any

from app.core.config import Settings, get_settings
from app.database.postgres import close_pool, get_pool
from app.database.queries import vector_literal
from app.providers.embeddings.ollama import (
    OllamaEmbeddingProvider,
    embedding_fingerprint,
)
from scripts.kemenag.categories import (
    category_index,
    labelled_content,
    load_category_manifest,
    parent_categories,
)
from scripts.kemenag.config import ROOT
from scripts.kemenag.db import corpus_rows
from scripts.kemenag.documents import is_official_provenance

LOCAL_CHILDREN = ROOT / "data/processed/kemenag_portal_seed_children.json"
EMBEDDING_BATCH_SIZE = 16


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
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is required")

    manifest = load_category_manifest()
    by_verse, pending = category_index(manifest)
    pool = await get_pool(settings)
    try:
        documents = await corpus_rows(pool, "quran_documents", manifest["corpus"])
        chunks = await corpus_rows(pool, "quran_chunks", manifest["corpus"])
        if any(
            not is_official_provenance(document.get("metadata") or {})
            for document in documents
        ):
            raise RuntimeError(
                "Active corpus contains a non-Kemenag source; refusing to relabel it"
            )

        grouped = parent_categories(chunks, by_verse)
        available_keys = {
            key.strip()
            for chunk in chunks
            for key in str(chunk.get("metadata", {}).get("verse_key", "")).split(",")
        }
        missing_keys = sorted(key for key in by_verse if key not in available_keys)
        changed_documents = await _update_documents(pool, documents, grouped, manifest)
        to_embed = _chunks_to_reembed(chunks, grouped, manifest)
        await _reembed_chunks(pool, to_embed, settings, manifest)
    finally:
        await close_pool()
    print(f"Updated documents: {changed_documents}; re-embedded chunks: {len(to_embed)}")
    print(f"Verse keys pending API fetch: {', '.join(missing_keys) or 'none'}")
    print(f"Categories with no configured keys: {', '.join(pending) or 'none'}")


async def _update_documents(
    pool: Any,
    documents: list[dict[str, Any]],
    grouped: dict[str, list[str]],
    manifest: dict[str, Any],
) -> int:
    updates: list[tuple[Any, Any, str]] = []
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
            updates.append((themes, metadata, document["id"]))
    if not updates:
        return 0
    await pool.executemany(
        """
        update public.quran_documents
        set themes = $1, metadata = $2, updated_at = now()
        where id = $3
        """,
        updates,
    )
    return len(updates)


def _chunks_to_reembed(
    chunks: list[dict[str, Any]],
    grouped: dict[str, list[str]],
    manifest: dict[str, Any],
) -> list[tuple[dict[str, Any], str, dict[str, Any]]]:
    """Return theme chunks whose content or metadata changed."""
    pending: list[tuple[dict[str, Any], str, dict[str, Any]]] = []
    for chunk in chunks:
        if chunk.get("chunk_type") != "themes":
            continue
        categories = grouped.get(chunk["parent_id"], [])
        content = labelled_content(chunk["content"], categories)
        metadata = dict(chunk.get("metadata") or {})
        metadata.update(
            {
                "mental_health_categories": categories,
                "category_manifest_version": manifest["version"],
            }
        )
        if content != chunk["content"] or metadata != chunk.get("metadata"):
            pending.append((chunk, content, metadata))
    return pending


async def _reembed_chunks(
    pool: Any,
    to_embed: list[tuple[dict[str, Any], str, dict[str, Any]]],
    settings: Settings,
    manifest: dict[str, Any],
) -> None:
    provider = OllamaEmbeddingProvider(
        settings.ollama_base_url,
        settings.ollama_embedding_model,
        settings.embedding_dimensions,
        settings.request_timeout_seconds,
    )
    embeddings: list[list[float]] = []
    for start in range(0, len(to_embed), EMBEDDING_BATCH_SIZE):
        batch = [item[1] for item in to_embed[start : start + EMBEDDING_BATCH_SIZE]]
        embeddings.extend(await provider.embed_documents(batch))
    if not to_embed:
        return

    await pool.executemany(
        """
        update public.quran_chunks
        set content = $1, metadata = $2, embedding = $3::vector,
            embedding_provider = $4, embedding_model = $5,
            embedding_version = $6, embedding_dimensions = $7,
            embedding_fingerprint = $8
        where id = $9
        """,
        [
            (
                content,
                metadata,
                vector_literal(vector),
                "ollama",
                settings.ollama_embedding_model,
                manifest["version"],
                settings.embedding_dimensions,
                embedding_fingerprint(
                    settings.ollama_embedding_model,
                    settings.embedding_dimensions,
                    content,
                ),
                chunk["id"],
            )
            for (chunk, content, metadata), vector in zip(
                to_embed, embeddings, strict=True
            )
        ],
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run", action="store_true", help="validate the local Kemenag snapshot only"
    )
    args = parser.parse_args()
    if args.dry_run:
        local_dry_run(load_category_manifest())
    else:
        asyncio.run(sync())


if __name__ == "__main__":
    main()
