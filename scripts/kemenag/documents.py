"""Convert fetched Kemenag payloads into corpus documents and chunks."""

from typing import Any

from app.quran.catalog import CHUNK_TYPES, CORPUS, child_id, parent_id
from scripts.kemenag.parsing import text

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

OFFICIAL_SOURCE_PROVIDER = "official_portal"
OFFICIAL_SOURCE_AUTHORITY = "LPMQ Kementerian Agama RI"


def is_official_provenance(metadata: dict[str, Any]) -> bool:
    return metadata.get("source_provider") == OFFICIAL_SOURCE_PROVIDER and (
        "kementerian agama" in str(metadata.get("source_authority", "")).casefold()
    )


def payload_to_document(
    key: str,
    row: dict[str, Any],
    manifest: dict[str, Any],
    categories: list[str] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Build one parent document plus its non-empty child chunks for ``key``."""
    surah, ayah = (int(part) for part in key.split(":"))
    surah_payload = row["surah_payload"]
    arabic = text(surah_payload, "Text MSI Usmani", "Arabic", "arabic")
    translation = text(surah_payload, "Terjemahan", "Translation", "translation")
    tafsir_text = _tafsir_text(row["tafsir_payload"])
    document_id = parent_id(manifest["corpus"], key)
    categories = sorted(categories or [])

    metadata = {
        "corpus": manifest["corpus"],
        "official": True,
        "verse_keys": [key],
        "source_provider": OFFICIAL_SOURCE_PROVIDER,
        "source_authority": OFFICIAL_SOURCE_AUTHORITY,
        "translation_language": "id",
        "translation_verified_source": True,
        "translation_provenance_status": "official_portal",
        "source_manifest_version": manifest["version"],
        "mental_health_categories": categories,
    }
    document = {
        "id": document_id,
        "surah_number": surah,
        "surah_name": text(surah_payload, "Nama Surah", "Nama Surat", "Surah Name")
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
    return document, _build_chunks(
        key,
        surah,
        ayah,
        document_id,
        metadata,
        manifest,
        arabic,
        translation,
        tafsir_text,
        categories,
    )


def _tafsir_text(tafsir: dict[str, Any]) -> str:
    return "\n\n".join(
        value
        for value in (
            text(tafsir, "Tafsir Ringkas"),
            text(tafsir, "Tafsir Tahlili"),
        )
        if value
    )


def _build_chunks(
    key: str,
    surah: int,
    ayah: int,
    document_id: str,
    metadata: dict[str, Any],
    manifest: dict[str, Any],
    arabic: str,
    translation: str,
    tafsir: str,
    categories: list[str],
) -> list[dict[str, Any]]:
    heading = f"Surah {surah}, ayat {ayah}"
    field_content = {
        "arabic": f"{heading}\nArab:\n{arabic}",
        "translation": f"{heading}\nTerjemahan Kemenag:\n{translation}",
        "tafsir": f"{heading}\nTafsir Kemenag:\n{tafsir}",
        "themes": (
            f"{heading}\n"
            f"Kategori kesehatan mental: {', '.join(categories) or 'belum dipetakan'}"
        )
        if categories
        else "",
    }
    return [
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
        for chunk_type, content in field_content.items()
        if _chunk_body(content)
    ]


def _chunk_body(content: str) -> str:
    return content.split(":\n", 1)[-1].strip()


def _chunk_types_for_document(document: dict[str, Any]) -> set[str]:
    fields = {
        "arabic": document.get("arabic_text"),
        "translation": document.get("translation"),
        "tafsir": document.get("tafsir"),
        "themes": document.get("themes"),
    }
    return {chunk_type for chunk_type, value in fields.items() if value}


def parents_by_verse(
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
    """Return requested verse keys whose parent row or child chunks are missing."""
    parents = parents_by_verse(documents, chunks)
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


def validate_chunk_rows(
    rows: list[tuple[dict[str, Any], list[dict[str, Any]]]], requested: list[str]
) -> dict[str, int]:
    """Guard the write set: every requested verse, one parent, valid children."""
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
    if any(not is_official_provenance(parent.get("metadata", {})) for parent, _ in rows):
        raise RuntimeError("Kemenag parent row is missing official provenance")
    if any(not is_official_provenance(child.get("metadata", {})) for child in children):
        raise RuntimeError("Kemenag child row is missing official provenance")
    return {
        chunk_type: sum(child["chunk_type"] == chunk_type for child in children)
        for chunk_type in CHUNK_TYPES
    }
