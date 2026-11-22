"""Sync the requested Kemenag verses into the active corpus."""

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from app.core.config import Settings, get_settings
from app.database.postgres import close_pool, get_pool
from app.providers.embeddings.ollama import (
    OllamaEmbeddingProvider,
    embedding_fingerprint,
)
from app.quran.catalog import expand_ranges, parent_id
from scripts.kemenag.cache import load_cache, save_cache
from scripts.kemenag.categories import category_index, load_category_manifest
from scripts.kemenag.config import DEFAULT_MANIFEST, EMBEDDING_BATCH_SIZE, ROOT
from scripts.kemenag.db import corpus_rows, delete_rows, upsert_chunks, upsert_documents
from scripts.kemenag.documents import (
    keys_needing_sync,
    parents_by_verse,
    payload_to_document,
    validate_chunk_rows,
)
from scripts.kemenag.parsing import number
from scripts.kemenag.portal import KemenagPortalClient

DOCUMENT_COLUMNS = "id,metadata,arabic_text,translation,tafsir,themes"
CHUNK_COLUMNS = "id,parent_id,chunk_type,metadata"


async def run(dry_run: bool, manifest_path: Path = DEFAULT_MANIFEST) -> None:
    manifest_path = manifest_path.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    requested = expand_ranges(manifest["ranges"])
    settings = get_settings()
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL wajib dikonfigurasi")

    pool = await get_pool(settings)
    try:
        await _sync(manifest, requested, settings, pool, dry_run, manifest_path)
    finally:
        await close_pool()


async def _sync(
    manifest, requested, settings: Settings, pool, dry_run: bool, manifest_path: Path
) -> None:
    existing_documents = await corpus_rows(
        pool, "quran_documents", manifest["corpus"], DOCUMENT_COLUMNS
    )
    existing_chunks = await corpus_rows(
        pool, "quran_chunks", manifest["corpus"], CHUNK_COLUMNS
    )
    pending = keys_needing_sync(
        requested, existing_documents, existing_chunks, manifest["corpus"]
    )
    _report_plan(manifest, requested, pending)
    if dry_run:
        return
    if not pending:
        print("Corpus dan parent-child chunks sudah lengkap.")
        return

    fetched = _fetch_pending(settings, manifest_path, pending)
    by_verse, _ = category_index(load_category_manifest())
    rows = [
        payload_to_document(key, fetched[key], manifest, by_verse.get(key, []))
        for key in pending
        if key in fetched
    ]
    if len(rows) != len(pending):
        raise RuntimeError("Kemenag fetch did not return every requested verse")

    child_counts = validate_chunk_rows(rows, pending)
    chunks = [child for _, row_chunks in rows for child in row_chunks]
    await _embed_chunks(chunks, settings, manifest["version"])
    await upsert_documents(pool, [parent for parent, _ in rows])
    await upsert_chunks(pool, chunks)
    await _delete_stale_rows(
        pool, manifest, rows, existing_documents, existing_chunks, pending
    )
    print(f"Inserted Kemenag documents: {len(rows)}; embedded chunks: {len(chunks)}")
    print("Child counts:", ", ".join(f"{key}={value}" for key, value in child_counts.items()))


def _report_plan(
    manifest: dict[str, Any], requested: list[str], pending: list[str]
) -> None:
    print(f"Manifest: {len(manifest['ranges'])} ranges, {len(requested)} ayat")
    ready = len(requested) - len(pending)
    print(f"Ready in corpus: {ready}; needing sync: {len(pending)}")
    print("Keys needing sync:", ", ".join(pending) or "none")


def _fetch_pending(
    settings: Settings, manifest_path: Path, pending: list[str]
) -> dict[str, dict[str, Any]]:
    raw_cache = ROOT / "data/raw" / f"{manifest_path.stem}_scrape.json"
    cache = load_cache(raw_cache)
    fetched = {key: cache[key] for key in pending if key in cache}
    missing = [key for key in pending if key not in fetched]
    if missing:
        fetched.update(_fetch_from_portal(settings, missing))
    cache.update(fetched)
    save_cache(list(cache.values()), raw_cache, manifest_path)
    return fetched


def _fetch_from_portal(
    settings: Settings, missing: list[str]
) -> dict[str, dict[str, Any]]:
    username = settings.kemenag_username or ""
    password = settings.kemenag_password or ""
    token = settings.kemenag_token or ""
    if not all((username, password, token)):
        raise RuntimeError(
            "Missing Kemenag credentials for new keys. Set KEMENAG_USERNAME, "
            "KEMENAG_PASSWORD, and KEMENAG_TOKEN in .env."
        )
    client = KemenagPortalClient.from_settings(
        settings.kemenag_api_base_url,
        username,
        password,
        token,
        settings.request_timeout_seconds,
    )
    try:
        client.login()
        return _fetch_verses_by_surah(client, missing)
    finally:
        client.close()


def _fetch_verses_by_surah(
    client: KemenagPortalClient, missing: list[str]
) -> dict[str, dict[str, Any]]:
    by_surah: dict[int, list[tuple[str, int]]] = {}
    for key in missing:
        surah, ayah = (int(part) for part in key.split(":"))
        by_surah.setdefault(surah, []).append((key, ayah))

    fetched: dict[str, dict[str, Any]] = {}
    for surah, items in by_surah.items():
        records = client.get_ayat(surah)
        for key, ayah in items:
            record = next(
                (
                    row
                    for row in records
                    if number(row, "No Ayat", "Ayat ID", "ayah") == ayah
                ),
                None,
            )
            if record is None:
                raise RuntimeError(f"Ayat {key} tidak ditemukan dari getAyat")
            ayat_id = str(number(record, "Ayat ID", "No Ayat", "ayah") or ayah)
            fetched[key] = {
                "verse_key": key,
                "surah_payload": record,
                "tafsir_payload": client.get_tafsir(ayat_id),
            }
    return fetched


async def _embed_chunks(
    chunks: list[dict[str, Any]], settings: Settings, manifest_version: str
) -> None:
    provider = OllamaEmbeddingProvider(
        settings.ollama_base_url,
        settings.ollama_embedding_model,
        settings.embedding_dimensions,
        settings.request_timeout_seconds,
    )
    embeddings: list[list[float]] = []
    for start in range(0, len(chunks), EMBEDDING_BATCH_SIZE):
        batch = [child["content"] for child in chunks[start : start + EMBEDDING_BATCH_SIZE]]
        embeddings.extend(await provider.embed_documents(batch))
    for child, vector in zip(chunks, embeddings, strict=True):
        child.update(
            {
                "embedding": vector,
                "embedding_provider": "ollama",
                "embedding_model": settings.ollama_embedding_model,
                "embedding_version": manifest_version,
                "embedding_dimensions": settings.embedding_dimensions,
                "embedding_fingerprint": embedding_fingerprint(
                    settings.ollama_embedding_model,
                    settings.embedding_dimensions,
                    child["content"],
                ),
            }
        )


async def _delete_stale_rows(
    pool: Any,
    manifest: dict[str, Any],
    rows: list[tuple[dict[str, Any], list[dict[str, Any]]]],
    existing_documents: list[dict[str, Any]],
    existing_chunks: list[dict[str, Any]],
    pending: list[str],
) -> None:
    new_parent_ids = {parent["id"] for parent, _ in rows}
    new_chunk_ids = {child["id"] for _, row_chunks in rows for child in row_chunks}
    stale_chunk_ids = {
        chunk["id"]
        for chunk in existing_chunks
        if chunk["parent_id"] in new_parent_ids and chunk["id"] not in new_chunk_ids
    }
    old_parent_ids = {
        document["id"]
        for key, document in parents_by_verse(existing_documents, existing_chunks).items()
        if key in pending and document["id"] != parent_id(manifest["corpus"], key)
    }
    await delete_rows(pool, "quran_chunks", manifest["corpus"], stale_chunk_ids)
    await delete_rows(pool, "quran_documents", manifest["corpus"], old_parent_ids)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="Manifest path, defaulting to the reflection subset manifest.",
    )
    args = parser.parse_args()
    asyncio.run(run(args.dry_run, args.manifest))
