"""Fetch the requested Kemenag verses and upsert them into the active corpus."""

import argparse
import json
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import httpx

from app.core.config import get_settings
from app.providers.embeddings.jina import JinaEmbeddingProvider, embedding_fingerprint
from supabase import acreate_client

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/manifests/kemenag_reflection_verses.json"
RAW_CACHE = ROOT / "data/raw/kemenag_reflection_scrape.json"
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


def expand_ranges(ranges: list[str]) -> list[str]:
    keys: list[str] = []
    for item in ranges:
        surah, ayahs = item.split(":", 1)
        bounds = [int(value) for value in ayahs.split("-", 1)]
        keys.extend(f"{int(surah)}:{ayah}" for ayah in range(bounds[0], bounds[-1] + 1))
    return list(dict.fromkeys(keys))


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
        parser = _TableParser()
        parser.feed(response.text)
        candidates = []
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


def load_cache() -> dict[str, dict[str, Any]]:
    if not RAW_CACHE.exists():
        return {}
    data = json.loads(RAW_CACHE.read_text(encoding="utf-8"))
    return {row["verse_key"]: row for row in data.get("responses", [])}


def save_cache(rows: list[dict[str, Any]]) -> None:
    RAW_CACHE.parent.mkdir(parents=True, exist_ok=True)
    RAW_CACHE.write_text(
        json.dumps(
            {
                "provider": "Quran Kemenag",
                "authority": "LPMQ Kementerian Agama RI",
                "manifest": str(MANIFEST.relative_to(ROOT)),
                "responses": rows,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def payload_to_document(
    key: str, row: dict[str, Any], manifest: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
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
    parent_id = f"qalbu-kemenag-{surah:03d}-{ayah:03d}-{ayah:03d}"
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
    }
    document = {
        "id": parent_id,
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
        "themes": [],
        "source": {
            "quran": "Quran Kemenag",
            "translation": "Terjemahan Kemenag",
            "tafsir": "Tafsir Kemenag (ringkas), Tafsir Kemenag (tahlili)",
        },
        "metadata": metadata,
        "corpus": manifest["corpus"],
    }
    content = (
        f"Surah {surah}, ayat {ayah}\n\nArab:\n{arabic}\n\n"
        f"Terjemahan Kemenag:\n{translation}\n\nTafsir Kemenag:\n{tafsir_text}"
    )
    child = {
        "id": f"child:kemenag:{surah}:{ayah}",
        "parent_id": parent_id,
        "chunk_type": "themes",
        "content": content,
        "metadata": {**metadata, "verse_key": key, "embedding_template": manifest["version"]},
        "corpus": manifest["corpus"],
    }
    return document, child


def existing_keys(documents: list[dict[str, Any]]) -> set[str]:
    return {
        key
        for document in documents
        for key in document.get("metadata", {}).get("verse_keys", [])
    }


async def run(dry_run: bool) -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    requested = expand_ranges(manifest["ranges"])
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_server_key:
        raise RuntimeError("SUPABASE_URL dan Supabase server key wajib dikonfigurasi")
    supabase = await acreate_client(settings.supabase_url, settings.supabase_server_key)
    documents = (
        await supabase.table("quran_documents")
        .select("metadata")
        .eq("corpus", manifest["corpus"])
        .execute()
    ).data
    missing = [key for key in requested if key not in existing_keys(documents)]
    print(f"Manifest: {len(manifest['ranges'])} ranges, {len(requested)} ayat")
    print(f"Already in corpus: {len(requested) - len(missing)}; missing: {len(missing)}")
    if dry_run:
        print("Missing keys:", ", ".join(missing) or "none")
        return
    if not missing:
        print("Tidak ada ayat baru untuk diambil.")
        return

    cache = load_cache()
    fetched: dict[str, dict[str, Any]] = {key: cache[key] for key in missing if key in cache}
    api_missing = [key for key in missing if key not in fetched]
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
    save_cache(list(fetched.values()))

    rows = [payload_to_document(key, fetched[key], manifest) for key in missing if key in fetched]
    provider = JinaEmbeddingProvider(
        settings.jina_api_key or "",
        settings.jina_embedding_model,
        settings.embedding_dimensions,
        settings.request_timeout_seconds,
    )
    embeddings: list[list[float]] = []
    for start in range(0, len(rows), 16):
        batch = [child["content"] for _, child in rows[start : start + 16]]
        embeddings.extend(
            await provider.embed_documents(batch)
        )
    children = []
    for (_, child), vector in zip(rows, embeddings, strict=True):
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
        children.append(child)
    await supabase.table("quran_documents").upsert(
        [parent for parent, _ in rows], on_conflict="id"
    ).execute()
    await supabase.table("quran_chunks").upsert(children, on_conflict="id").execute()
    print(f"Inserted Kemenag documents: {len(rows)}; embedded chunks: {len(children)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    import asyncio

    asyncio.run(run(args.dry_run))


if __name__ == "__main__":
    main()
