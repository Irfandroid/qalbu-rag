import json
from pathlib import Path

from scripts.scrape_kemenag_manifest import expand_ranges, payload_to_document

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
    document, child = payload_to_document(
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
    )
    assert document["source"]["quran"] == "Quran Kemenag"
    assert document["source"]["tafsir"] == "Tafsir Kemenag (ringkas), Tafsir Kemenag (tahlili)"
    assert document["metadata"]["source_authority"] == "LPMQ Kementerian Agama RI"
    assert "Tafsir Kemenag" in child["content"]
    assert child["metadata"]["verse_key"] == "39:53"
