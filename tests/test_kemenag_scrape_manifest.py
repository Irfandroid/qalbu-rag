import json
from pathlib import Path

import httpx

from scripts.scrape_kemenag_manifest import expand_ranges, parse_payload, payload_to_document

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
