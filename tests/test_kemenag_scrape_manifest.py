import json
from pathlib import Path

import httpx

from app.quran.catalog import CHUNK_TYPES, parent_id
from scripts.scrape_kemenag_manifest import (
    expand_ranges,
    keys_needing_sync,
    parse_payload,
    payload_to_document,
)

MANIFEST = Path(__file__).parents[1] / "data/manifests/kemenag_reflection_verses.json"


def test_requested_manifest_expands_to_all_unique_verses():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    keys = expand_ranges(manifest["ranges"])
    assert len(manifest["ranges"]) == 100
    assert len(keys) == 201
    assert keys[0] == "1:1"
    assert keys[-1] == "114:6"


def test_kemenag_payload_keeps_provenance_and_tafsir():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    document, children = payload_to_document(
        "39:53",
        {
            "surah_payload": {
                "Ayat ID": "53",
                "Text MSI Usmani": "arabic",
                "Terjemahan": "translation",
            },
            "tafsir_payload": {
                "Tafsir Ringkas": "ringkas",
                "Tafsir Tahlili": "tahlili",
            },
        },
        manifest,
        categories=["rasa_bersalah"],
    )
    assert document["source"]["quran"] == "Quran Kemenag"
    assert document["source"]["tafsir"] == "Tafsir Kemenag (ringkas), Tafsir Kemenag (tahlili)"
    assert document["metadata"]["source_authority"] == "LPMQ Kementerian Agama RI"
    assert {child["chunk_type"] for child in children} == {
        "arabic", "translation", "tafsir", "themes"
    }
    tafsir = next(child for child in children if child["chunk_type"] == "tafsir")
    assert "Tafsir Kemenag" in tafsir["content"]
    assert tafsir["metadata"]["verse_key"] == "39:53"
    assert all(child["parent_id"] == document["id"] for child in children)


def test_parse_kemenag_html_fragment():
    response = httpx.Response(
        200,
        text=(
            "Ayat ID : <b>2251</b><br>No Ayat : <b>1</b><br>"
            "Text MSI Usmani: <b class='arabic'>arab</b><br>"
            "Terjemahan : <b>arti</b><br>"
            "Tafsir Ringkas: <b>ringkas</b><br>"
            "Tafsir Tahlili : tahlili<br>"
        ),
    )
    rows = parse_payload(response)
    assert rows == [
        {
            "Ayat ID": "2251",
            "No Ayat": "1",
            "Text MSI Usmani": "arab",
            "Terjemahan": "arti",
            "Tafsir Ringkas": "ringkas",
            "Tafsir Tahlili": "tahlili",
        }
    ]


def test_scraper_ignores_complete_superset_when_planning_requested_manifest():
    key = "39:53"
    document_id = parent_id("qalbu-kemenag-v1", key)
    documents = [
        {
            "id": document_id,
            "metadata": {"verse_keys": [key]},
            "arabic_text": "arabic",
            "translation": "translation",
            "tafsir": "tafsir",
            "themes": ["rasa_bersalah"],
        },
        {"id": "extra-parent", "metadata": {"verse_keys": ["2:2"]}},
    ]
    chunks = [
        {"parent_id": document_id, "chunk_type": chunk_type}
        for chunk_type in CHUNK_TYPES
    ]
    assert keys_needing_sync([key], documents, chunks) == []


def test_scraper_repairs_missing_or_legacy_parent_chunks():
    key = "39:53"
    documents = [{"id": "legacy-parent", "metadata": {"verse_keys": [key]}}]
    assert keys_needing_sync([key], documents, []) == [key]


def test_scraper_repairs_a_missing_child_on_an_existing_parent():
    key = "39:53"
    document_id = parent_id("qalbu-kemenag-v1", key)
    documents = [
        {
            "id": document_id,
            "metadata": {"verse_keys": [key]},
            "arabic_text": "arabic",
            "translation": "translation",
            "tafsir": "tafsir",
            "themes": ["rasa_bersalah"],
        }
    ]
    chunks = [
        {"parent_id": document_id, "chunk_type": chunk_type}
        for chunk_type in CHUNK_TYPES
        if chunk_type != "themes"
    ]
    assert keys_needing_sync([key], documents, chunks) == [key]
