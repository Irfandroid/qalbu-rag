import json
from pathlib import Path

from app.quran.themes import THEMES

MANIFEST = Path(__file__).parents[1] / "data/manifests/mental_health_categories.json"


def test_manifest_covers_the_requested_taxonomy():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    groups = {}
    for category in data["categories"]:
        groups.setdefault(category["group"], set()).add(category["id"])

    assert groups["emotional_distress"] == {
        "kecemasan", "kesedihan", "kemarahan", "rasa_bersalah", "kehampaan"
    }
    assert groups["self"] == {"kegagalan", "harga_diri", "perbandingan", "malu"}
    assert groups["life_challenges"] == {
        "stres", "burnout", "ketidakpastian", "kesulitan", "tekanan_finansial_karier"
    }
    assert groups["relationships"] == {"kesepian", "penolakan", "konflik", "patah_hati", "duka"}
    assert groups["existential_spiritual"] == {
        "tujuan_hidup", "makna_hidup", "iman", "taubat", "penerimaan"
    }
    assert groups["safety"] == {"self_harm", "suicidal_ideation", "psychosis", "severe_crisis"}


def test_safety_categories_cannot_enter_retrieval_themes():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    safety = {item["id"] for item in data["categories"] if item.get("guardrail_only")}
    assert safety.isdisjoint(THEMES)
