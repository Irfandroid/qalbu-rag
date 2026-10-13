"""Fetch the requested Kemenag verses and upsert them into the active corpus."""

import argparse
import html
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import httpx

from app.core.config import get_settings
from app.providers.embeddings.jina import JinaEmbeddingProvider, embedding_fingerprint
from app.quran.catalog import CHUNK_TYPES, CORPUS, child_id, expand_ranges, parent_id
from supabase import acreate_client

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "data/manifests/kemenag_reflection_verses.json"
DEFAULT_RAW_CACHE = ROOT / "data/raw/kemenag_reflection_scrape.json"
# Kept as aliases for callers and tests that use the original MVP manifest.
MANIFEST = DEFAULT_MANIFEST
RAW_CACHE = DEFAULT_RAW_CACHE
DEFAULT_BASE_URL = "https://quran-api.lpmqkemenag.id/alquran/data"
SURAH_NAMES = {
    19: "Maryam",
    34: "Saba'",
    72: "Al-Jinn",
    96: "Al-'Alaq",
    99: "Az-Zalzalah",
    108: "Al-Kawthar",
    109: "Al-Kafirun",
    112: "Al-Ikhlas",
}


class _TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[str]] = []
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            self._row = []
        elif tag in {"td", "th"} and self._row is not None:
            self._cell = []

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self._cell is not None and self._row is not None:
            self._row.append(" ".join("".join(self._cell).split()))
            self._cell = None
        elif tag == "tr" and self._row:
            self.rows.append(self._row)
            self._row = None


def _candidate_dicts(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        candidates = (
            [value]
            if any(key in value for key in ("Ayat ID", "No Ayat", "Text MSI Usmani"))
            else []
        )
        for child in value.values():
            candidates.extend(_candidate_dicts(child))
        return candidates
    if isinstance(value, list):
        return [candidate for child in value for candidate in _candidate_dicts(child)]
    return []


def parse_payload(response: httpx.Response) -> list[dict[str, Any]]:
    try:
        candidates = _candidate_dicts(response.json())
    except ValueError:
        candidates = _parse_labelled_html(response.text)
        if not candidates:
            parser = _TableParser()
            parser.feed(response.text)
            for row in parser.rows:
                if len(row) >= 2:
                    candidates.append(dict(zip(row[::2], row[1::2], strict=False)))
            for index, headers in enumerate(parser.rows[:-1]):
                next_row = parser.rows[index + 1]
                if len(headers) == len(next_row) and any("Ayat" in header for header in headers):
                    candidates.append(dict(zip(headers, next_row, strict=True)))
    if not candidates:
        raise RuntimeError("Kemenag API returned no ayat payload")
    return candidates


def _parse_labelled_html(source: str) -> list[dict[str, Any]]:
    """Parse Kemenag's authenticated response, which is an HTML fragment, not JSON."""
    fields = (
        "Ayat ID",
        "Surah ID",
        "No Ayat",
        "No Juz",
        "Halaman",
        "Text MSI Usmani",
        "Transliterasi",
        "Terjemahan",
        "No Foot",
        "Teks Foot",
        "Keterangan",
        "Tafsir Ringkas",
        "Tafsir Tahlili",
    )
    label = "|".join(re.escape(field) for field in fields)
    field_pattern = re.compile(
        rf"(?P<label>{label})\s*:\s*(?:<b[^>]*>(?P<bold>.*?)</b>|(?P<plain>.*?))"
        r"(?=<br\s*/?>|$)",
        re.IGNORECASE | re.DOTALL,
    )
    records: list[dict[str, Any]] = []
    for fragment in re.split(r"(?=Ayat ID\s*:)", source, flags=re.IGNORECASE)[1:]:
        record: dict[str, Any] = {}
        for match in field_pattern.finditer(fragment):
            value = match.group("bold") or match.group("plain") or ""
            value = re.sub(r"<[^>]+>", "", value)
            record[match.group("label")] = html.unescape(value).strip()
        if "Ayat ID" in record:
            records.append(record)
    return records


def _number(record: dict[str, Any], *fields: str) -> int | None:
    for field in fields:
        value = record.get(field)
        if value is not None and str(value).strip().isdigit():
            return int(str(value).strip())
    return None


def _text(record: dict[str, Any], *fields: str) -> str:
    for field in fields:
        value = record.get(field)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


class KemenagPortalClient:
    def __init__(
        self, base_url: str, username: str, password: str, token: str, timeout: float
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.token = token
        self.client = httpx.Client(
            timeout=timeout,
            follow_redirects=True,
            headers={"Accept": "application/json, text/html"},
        )

    def close(self) -> None:
        self.client.close()

    def login(self) -> None:
        portal_root = self.base_url.removesuffix("/data")
        response = self.client.post(
            f"{portal_root}/dashboard/cek_login",
            data={"username": self.username, "password": self.password, "id": self.token},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()
        if "dashboard/login" in str(response.url).casefold():
            raise RuntimeError("Kemenag login gagal; periksa username, password, dan token")

    def get_ayat(self, surah: int) -> list[dict[str, Any]]:
        response = self.client.post(f"{self.base_url}/getAyat", data={"surah": str(surah)})
        response.raise_for_status()
        return parse_payload(response)

    def get_tafsir(self, ayat_id: str) -> dict[str, Any]:
        response = self.client.post(
            f"{self.base_url}/getAyatTafsir", data={"ayat": ayat_id}
        )
        response.raise_for_status()
        return parse_payload(response)[0]


def load_cache(path: Path = RAW_CACHE) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {row["verse_key"]: row for row in data.get("responses", [])}


def save_cache(rows: list[dict[str, Any]], path: Path, manifest_path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "provider": "Quran Kemenag",
                "authority": "LPMQ Kementerian Agama RI",
                "manifest": str(manifest_path.relative_to(ROOT)),
                "responses": rows,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def payload_to_document(
    key: str,
    row: dict[str, Any],
    manifest: dict[str, Any],
    categories: list[str] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    surah, ayah = (int(part) for part in key.split(":"))
    arabic = _text(row["surah_payload"], "Text MSI Usmani", "Arabic", "arabic")
    translation = _text(row["surah_payload"], "Terjemahan", "Translation", "translation")
    tafsir = row["tafsir_payload"]
    tafsir_text = "\n\n".join(
        value
        for value in (
            _text(tafsir, "Tafsir Ringkas"),
            _text(tafsir, "Tafsir Tahlili"),
        )
        if value
    )
    document_id = parent_id(manifest["corpus"], key)
    categories = sorted(categories or [])
    metadata = {
        "corpus": manifest["corpus"],
        "official": True,
        "verse_keys": [key],
        "source_provider": "official_portal",
        "source_authority": "LPMQ Kementerian Agama RI",
        "translation_language": "id",
        "translation_verified_source": True,
        "translation_provenance_status": "official_portal",
        "source_manifest_version": manifest["version"],
        "mental_health_categories": categories,
    }
    document = {
        "id": document_id,
        "surah_number": surah,
        "surah_name": _text(
            row["surah_payload"], "Nama Surah", "Nama Surat", "Surah Name"
        )
        or SURAH_NAMES.get(surah, f"Surah {surah}"),
        "ayah_start": ayah,
        "ayah_end": ayah,
        "arabic_text": arabic,
        "translation": translation,
        "tafsir": tafsir_text,
        "themes": categories,
        "source": {
            "quran": "Quran Kemenag",
            "translation": "Terjemahan Kemenag",
            "tafsir": "Tafsir Kemenag (ringkas), Tafsir Kemenag (tahlili)",
        },
        "metadata": metadata,
        "corpus": manifest["corpus"],
    }
    field_content = {
        "arabic": f"Surah {surah}, ayat {ayah}\nArab:\n{arabic}",
        "translation": f"Surah {surah}, ayat {ayah}\nTerjemahan Kemenag:\n{translation}",
        "tafsir": f"Surah {surah}, ayat {ayah}\nTafsir Kemenag:\n{tafsir_text}",
        "themes": (
            f"Surah {surah}, ayat {ayah}\n"
            f"Kategori kesehatan mental: {', '.join(categories) or 'belum dipetakan'}"
        )
        if categories
        else "",
    }
    chunks = [
        {
            "id": child_id(document_id, chunk_type),
            "parent_id": document_id,
            "chunk_type": chunk_type,
            "content": content,
            "metadata": {
                **metadata,
                "verse_key": key,
                "chunk_type": chunk_type,
                "embedding_template": manifest["version"],
            },
            "corpus": manifest["corpus"],
        }
        for chunk_type in CHUNK_TYPES
        for content in [field_content[chunk_type]]
        if content.split(":\n", 1)[-1].strip()
    ]
    return document, chunks


def _chunk_types_for_document(document: dict[str, Any]) -> set[str]:
    fields = {
        "arabic": document.get("arabic_text"),
        "translation": document.get("translation"),
        "tafsir": document.get("tafsir"),
        "themes": document.get("themes"),
    }
    return {chunk_type for chunk_type, value in fields.items() if value}


def _parents_by_verse(
    documents: list[dict[str, Any]], chunks: list[dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    parents: dict[str, dict[str, Any]] = {}
    for document in documents:
        for key in document.get("metadata", {}).get("verse_keys", []):
            parents[key] = document
    for chunk in chunks:
        key = chunk.get("metadata", {}).get("verse_key")
        if key and key not in parents:
            parents[key] = {"id": chunk["parent_id"]}
    return parents


def keys_needing_sync(
    requested: list[str],
    documents: list[dict[str, Any]],
    chunks: list[dict[str, Any]],
    corpus: str = CORPUS,
) -> list[str]:
    parents = _parents_by_verse(documents, chunks)
    chunks_by_parent: dict[str, set[str]] = {}
    for chunk in chunks:
        chunks_by_parent.setdefault(chunk["parent_id"], set()).add(chunk["chunk_type"])
    pending: list[str] = []
    for key in requested:
        document = parents.get(key)
        expected_id = parent_id(corpus, key)
        if not document or document.get("id") != expected_id:
            pending.append(key)
            continue
        if chunks_by_parent.get(expected_id, set()) != _chunk_types_for_document(document):
            pending.append(key)
    return pending


async def corpus_rows(client: Any, table: str, columns: str, corpus: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    start = 0
    while True:
        batch = (
            await client.table(table)
            .select(columns)
            .eq("corpus", corpus)
            .range(start, start + 999)
            .execute()
        ).data or []
        rows.extend(batch)
        if len(batch) < 1000:
            return rows
        start += 1000


def validate_chunk_rows(
    rows: list[tuple[dict[str, Any], list[dict[str, Any]]]], requested: list[str]
) -> dict[str, int]:
    requested_keys = set(requested)
    parent_keys = [
        key
        for parent, _ in rows
        for key in parent.get("metadata", {}).get("verse_keys", [])
    ]
    if len(parent_keys) != len(set(parent_keys)) or set(parent_keys) != requested_keys:
        raise RuntimeError("Kemenag parent rows do not match the requested verse inventory")
    parent_ids = {parent["id"] for parent, _ in rows}
    children = [child for _, chunks in rows for child in chunks]
    pairs = [(child["parent_id"], child["chunk_type"]) for child in children]
    if any(child["parent_id"] not in parent_ids for child in children):
        raise RuntimeError("Kemenag child row references an unknown parent")
    if len(pairs) != len(set(pairs)):
        raise RuntimeError("Kemenag child rows contain duplicate parent/type pairs")
    if any(child["chunk_type"] not in CHUNK_TYPES for child in children):
        raise RuntimeError("Kemenag child row contains an unsupported chunk type")
    if any(
        parent.get("metadata", {}).get("source_provider") != "official_portal"
        or "kementerian agama"
        not in parent.get("metadata", {}).get("source_authority", "").casefold()
        for parent, _ in rows
    ):
        raise RuntimeError("Kemenag parent row is missing official provenance")
    if any(
        child.get("metadata", {}).get("source_provider") != "official_portal"
        or "kementerian agama"
        not in child.get("metadata", {}).get("source_authority", "").casefold()
        for child in children
    ):
        raise RuntimeError("Kemenag child row is missing official provenance")
    return {
        chunk_type: sum(child["chunk_type"] == chunk_type for child in children)
        for chunk_type in CHUNK_TYPES
    }


def _category_index() -> dict[str, list[str]]:
    path = ROOT / "data/manifests/mental_health_categories.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    result: dict[str, list[str]] = {}
    for category in data["categories"]:
        if category.get("guardrail_only"):
            continue
        for key in category.get("verse_keys", []):
            result.setdefault(key, []).append(category["id"])
    return result


async def run(dry_run: bool, manifest_path: Path = MANIFEST) -> None:
    manifest_path = manifest_path.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    raw_cache = ROOT / "data/raw" / f"{manifest_path.stem}_scrape.json"
    requested = expand_ranges(manifest["ranges"])
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_server_key:
        raise RuntimeError("SUPABASE_URL dan Supabase server key wajib dikonfigurasi")
    supabase = await acreate_client(settings.supabase_url, settings.supabase_server_key)
    documents = await corpus_rows(
        supabase,
        "quran_documents",
        "id,metadata,arabic_text,translation,tafsir,themes",
        manifest["corpus"],
    )
    existing_chunks = await corpus_rows(
        supabase,
        "quran_chunks",
        "id,parent_id,chunk_type,metadata",
        manifest["corpus"],
    )
    pending = keys_needing_sync(requested, documents, existing_chunks, manifest["corpus"])
    print(f"Manifest: {len(manifest['ranges'])} ranges, {len(requested)} ayat")
    print(f"Ready in corpus: {len(requested) - len(pending)}; needing sync: {len(pending)}")
    if dry_run:
        print("Keys needing sync:", ", ".join(pending) or "none")
        return
    if not pending:
        print("Corpus dan parent-child chunks sudah lengkap.")
        return

    cache = load_cache(raw_cache)
    fetched: dict[str, dict[str, Any]] = {key: cache[key] for key in pending if key in cache}
    api_missing = [key for key in pending if key not in fetched]
    username = settings.kemenag_username or ""
    password = settings.kemenag_password or ""
    token = settings.kemenag_token or ""
    if api_missing and not all((username, password, token)):
        raise RuntimeError(
            "Missing Kemenag credentials for new keys. Set KEMENAG_USERNAME, "
            "KEMENAG_PASSWORD, and KEMENAG_TOKEN in .env."
        )
    if api_missing:
        client = KemenagPortalClient(
            settings.kemenag_api_base_url or DEFAULT_BASE_URL,
            username,
            password,
            token,
            settings.request_timeout_seconds,
        )
        try:
            client.login()
            by_surah: dict[int, list[dict[str, Any]]] = {}
            for key in api_missing:
                surah, ayah = (int(part) for part in key.split(":"))
                by_surah.setdefault(surah, []).append({"key": key, "ayah": ayah})
            for surah, items in by_surah.items():
                records = client.get_ayat(surah)
                for item in items:
                    record = next(
                        (
                            row
                            for row in records
                            if _number(row, "No Ayat", "Ayat ID", "ayah") == item["ayah"]
                        ),
                        None,
                    )
                    if record is None:
                        raise RuntimeError(f"Ayat {item['key']} tidak ditemukan dari getAyat")
                    ayat_id = str(_number(record, "Ayat ID", "No Ayat", "ayah") or item["ayah"])
                    fetched[item["key"]] = {
                        "verse_key": item["key"],
                        "surah_payload": record,
                        "tafsir_payload": client.get_tafsir(ayat_id),
                    }
        finally:
            client.close()
    cache.update(fetched)
    save_cache(list(cache.values()), raw_cache, manifest_path)

    categories = _category_index()
    rows = [
        payload_to_document(key, fetched[key], manifest, categories.get(key, []))
        for key in pending
        if key in fetched
    ]
    if len(rows) != len(pending):
        raise RuntimeError("Kemenag fetch did not return every requested verse")
    child_counts = validate_chunk_rows(rows, pending)
    chunks = [child for _, row_chunks in rows for child in row_chunks]
    provider = JinaEmbeddingProvider(
        settings.jina_api_key or "",
        settings.jina_embedding_model,
        settings.embedding_dimensions,
        settings.request_timeout_seconds,
    )
    embeddings: list[list[float]] = []
    for start in range(0, len(chunks), 16):
        batch = [child["content"] for child in chunks[start : start + 16]]
        embeddings.extend(
            await provider.embed_documents(batch)
        )
    for child, vector in zip(chunks, embeddings, strict=True):
        child.update(
            {
                "embedding": vector,
                "embedding_provider": "jina",
                "embedding_model": settings.jina_embedding_model,
                "embedding_version": manifest["version"],
                "embedding_dimensions": settings.embedding_dimensions,
                "embedding_fingerprint": embedding_fingerprint(
                    settings.jina_embedding_model, settings.embedding_dimensions, child["content"]
                ),
            }
        )
    parents = [parent for parent, _ in rows]
    for start in range(0, len(parents), 64):
        await supabase.table("quran_documents").upsert(
            parents[start : start + 64], on_conflict="id"
        ).execute()
    for start in range(0, len(chunks), 32):
        await supabase.table("quran_chunks").upsert(
            chunks[start : start + 32], on_conflict="id"
        ).execute()
    new_parent_ids = {parent["id"] for parent, _ in rows}
    new_chunk_ids = {child["id"] for child in chunks}
    stale_chunk_ids = {
        chunk["id"]
        for chunk in existing_chunks
        if chunk["parent_id"] in new_parent_ids
        and chunk["id"] not in new_chunk_ids
    }
    old_parent_ids = {
        document["id"]
        for key, document in _parents_by_verse(documents, existing_chunks).items()
        if key in pending and document["id"] != parent_id(manifest["corpus"], key)
    }
    if stale_chunk_ids:
        await (
            supabase.table("quran_chunks")
            .delete()
            .eq("corpus", manifest["corpus"])
            .in_("id", list(stale_chunk_ids))
            .execute()
        )
    if old_parent_ids:
        await (
            supabase.table("quran_documents")
            .delete()
            .eq("corpus", manifest["corpus"])
            .in_("id", list(old_parent_ids))
            .execute()
        )
    print(f"Inserted Kemenag documents: {len(rows)}; embedded chunks: {len(chunks)}")
    print("Child counts:", ", ".join(f"{key}={value}" for key, value in child_counts.items()))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=MANIFEST,
        help="Manifest path, defaulting to the reflection subset manifest.",
    )
    args = parser.parse_args()
    import asyncio

    asyncio.run(run(args.dry_run, args.manifest))


if __name__ == "__main__":
    main()
