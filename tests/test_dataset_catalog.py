import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.quran.catalog import (
    CHUNK_TYPES,
    child_id,
    expand_ranges,
    parent_id,
)
from scripts.scrape_kemenag_manifest import payload_to_document, validate_chunk_rows

MANIFEST = Path("data/manifests/kemenag_corpus_verses.json")


def test_canonical_manifest_has_282_unique_verses():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    keys = expand_ranges(manifest["ranges"])
    assert len(keys) == 282
    assert len(set(keys)) == 282
    assert manifest["corpus"] == "qalbu-kemenag-v1"


def test_parent_and_child_ids_are_deterministic():
    parent = parent_id("qalbu-kemenag-v1", "39:53")
    assert parent == "qalbu-kemenag-v1-039-053"
    assert child_id(parent, "tafsir") == "qalbu-kemenag-v1-039-053:tafsir"


def test_chunk_builder_skips_empty_fields_and_validates_provenance():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    rows = [
        payload_to_document(
            "39:53",
            {
                "surah_payload": {
                    "Ayat ID": "4164",
                    "Text MSI Usmani": "arabic",
                    "Terjemahan": "translation",
                },
                "tafsir_payload": {},
            },
            manifest,
        )
    ]
    assert {chunk["chunk_type"] for chunk in rows[0][1]} == {"arabic", "translation", "themes"}
    assert all(
        chunk["metadata"]["source_authority"] == "LPMQ Kementerian Agama RI"
        for chunk in rows[0][1]
    )
    assert validate_chunk_rows(rows, ["39:53"]) == {
        "arabic": 1,
        "translation": 1,
        "tafsir": 0,
        "themes": 1,
    }


def test_dataset_api_exposes_references_only():
    response = TestClient(app).get("/api/v1/dataset/verses?search=39:53")
    assert response.status_code == 200
    body = response.json()
    assert body["parent_count"] == 282
    assert body["child_counts"] == {chunk_type: 282 for chunk_type in CHUNK_TYPES}
    assert body["matched_verses"] == 1
    assert body["verses"][0]["verse_key"] == "39:53"
    assert "translation" not in body["verses"][0]
    assert "tafsir" not in body["verses"][0]


def test_dataset_page_is_served():
    response = TestClient(app).get("/dataset")
    assert response.status_code == 200
    assert "Dataset Quran" in response.text
