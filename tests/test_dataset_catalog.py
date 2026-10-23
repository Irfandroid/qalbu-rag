import json
from datetime import UTC, date, datetime
from pathlib import Path

from fastapi.testclient import TestClient

import app.api.dependencies as dataset_dependencies
from app.api.dependencies import (
    get_daily_verse_document,
    get_dataset_child_counts,
    get_dataset_document,
)
from app.core.config import get_settings
from app.main import app
from app.models.quran import QuranDocument
from app.quran.catalog import (
    child_id,
    daily_date_in_timezone,
    expand_ranges,
    parent_id,
    select_verse_of_day,
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
    assert {chunk["chunk_type"] for chunk in rows[0][1]} == {"arabic", "translation"}
    assert all(
        chunk["metadata"]["source_authority"] == "LPMQ Kementerian Agama RI"
        for chunk in rows[0][1]
    )
    assert validate_chunk_rows(rows, ["39:53"]) == {
        "arabic": 1,
        "translation": 1,
        "tafsir": 0,
        "themes": 0,
    }


def test_chunk_builder_creates_themes_only_for_real_categories():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    _, children = payload_to_document(
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
        categories=["rasa_bersalah"],
    )
    assert {chunk["chunk_type"] for chunk in children} == {
        "arabic", "translation", "themes"
    }


def test_dataset_api_exposes_references_only():
    app.dependency_overrides[get_dataset_child_counts] = lambda: None
    try:
        response = TestClient(app).get("/api/v1/dataset/verses?search=39:53")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    body = response.json()
    assert body["parent_count"] == 282
    assert body["child_counts"] == {
        "arabic": 282,
        "translation": 282,
        "tafsir": 282,
        "themes": 225,
    }
    assert body["matched_verses"] == 1
    assert body["verses"][0]["verse_key"] == "39:53"
    assert "translation" not in body["verses"][0]
    assert "tafsir" not in body["verses"][0]


def test_dataset_api_uses_actual_child_counts():
    app.dependency_overrides[get_dataset_child_counts] = lambda: {
        "arabic": 282,
        "translation": 282,
        "tafsir": 281,
        "themes": 225,
    }
    try:
        body = TestClient(app).get("/api/v1/dataset/verses").json()
    finally:
        app.dependency_overrides.clear()
    assert body["child_counts"] == {
        "arabic": 282,
        "translation": 282,
        "tafsir": 281,
        "themes": 225,
    }


def test_dataset_api_is_disabled_for_seed_rollback(monkeypatch):
    monkeypatch.setenv("QALBU_CORPUS", "qalbu-seed-v1")
    get_settings.cache_clear()
    try:
        response = TestClient(app).get("/api/v1/dataset/verses")
    finally:
        get_settings.cache_clear()
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "DATASET_CATALOG_UNAVAILABLE"


def test_dataset_page_is_served():
    response = TestClient(app).get("/dataset")
    assert response.status_code == 200
    assert "Dataset Quran" in response.text


def test_verse_of_day_rotation_is_deterministic():
    keys = ["1:1", "2:2", "3:3"]

    assert select_verse_of_day(keys, date(2026, 1, 1)) == "1:1"
    assert select_verse_of_day(keys, date(2026, 1, 2)) == "2:2"
    assert select_verse_of_day(keys, date(2026, 1, 4)) == "1:1"


def test_verse_of_day_uses_asia_jakarta_midnight():
    before_midnight = datetime(2026, 10, 23, 16, 59, tzinfo=UTC)
    after_midnight = datetime(2026, 10, 23, 17, 0, tzinfo=UTC)

    assert daily_date_in_timezone(before_midnight) == date(2026, 10, 23)
    assert daily_date_in_timezone(after_midnight) == date(2026, 10, 24)


def _official_document() -> QuranDocument:
    return QuranDocument(
        id="qalbu-kemenag-v1-013-028",
        surah_number=13,
        surah_name="Ar-Ra'd",
        ayah_start=28,
        ayah_end=28,
        arabic_text="عربي",
        translation="Hanya dengan mengingat Allah hati menjadi tenteram.",
        tafsir="Tafsir tersedia.",
        themes=["ketenangan_zikir"],
        source={"quran": "Quran Kemenag", "translation": "Terjemahan Kemenag"},
        metadata={
            "source_provider": "official_portal",
            "source_authority": "LPMQ Kementerian Agama RI",
        },
    )


def test_daily_verse_api_returns_source_and_detail_link():
    app.dependency_overrides[get_daily_verse_document] = lambda: _official_document()
    try:
        response = TestClient(app).get("/api/v1/dataset/verse-of-day")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["verse_key"] == "13:28"
    assert body["translation"] == "Hanya dengan mengingat Allah hati menjadi tenteram."
    assert body["timezone"] == "Asia/Jakarta"
    assert body["detail_url"] == "/dataset/verse/13/28"
    assert "Kementerian Agama" in body["source_status"]


def test_daily_verse_api_reports_missing_source(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "")
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "")
    get_settings.cache_clear()
    try:
        response = TestClient(app).get("/api/v1/dataset/verse-of-day")
    finally:
        get_settings.cache_clear()

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "DATASET_DETAIL_UNAVAILABLE"


def test_daily_verse_api_reports_database_failure(monkeypatch):
    async def unavailable(_settings):
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(dataset_dependencies, "get_supabase", unavailable)
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "service-key")
    get_settings.cache_clear()
    try:
        response = TestClient(app).get("/api/v1/dataset/verse-of-day")
    finally:
        get_settings.cache_clear()

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "DATASET_DETAIL_UNAVAILABLE"


def test_dataset_detail_api_returns_actual_document():
    app.dependency_overrides[get_dataset_document] = lambda: _official_document()
    try:
        response = TestClient(app).get("/api/v1/dataset/verses/13/28")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["verse_key"] == "13:28"
    assert body["arabic_text"] == "عربي"
    assert body["source"]["quran"] == "Quran Kemenag"
    assert "tafsir" in body


def test_dataset_detail_page_is_served():
    response = TestClient(app).get("/dataset/verse/13/28")

    assert response.status_code == 200
    assert "Detail Ayat" in response.text


def test_catalog_links_to_detail_page():
    app.dependency_overrides[get_dataset_child_counts] = lambda: None
    try:
        response = TestClient(app).get("/dataset")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert "/dataset/verse/" in response.text


def test_dataset_page_contains_manual_request_form():
    response = TestClient(app).get("/dataset")

    assert response.status_code == 200
    assert 'id="request-dataset"' in response.text
    assert 'id="request-reference"' in response.text
    assert 'id="request-reason"' in response.text
    assert "navigator.clipboard" in response.text
    assert "Clipboard tidak tersedia" in response.text


def test_homepage_links_to_manual_dataset_request():
    response = TestClient(app).get("/")

    assert response.status_code == 200
    assert "/dataset#request-dataset" in response.text


def test_homepage_contains_daily_verse_region():
    response = TestClient(app).get("/")

    assert response.status_code == 200
    assert 'id="daily-verse"' in response.text
    assert "/api/v1/dataset/verse-of-day" in response.text
    assert "source_status" in response.text
