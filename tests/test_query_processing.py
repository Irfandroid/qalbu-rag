import pytest

from app.rag.query_processing import (
    Intent,
    classify_intent,
    enrich_query,
    is_out_of_scope,
    understand_query,
)


@pytest.mark.parametrize(
    ("query", "intent"),
    [
        ("Ayat 39:53 terjemahannya apa?", Intent.QURANIC_INFORMATION),
        ("Apa arti sabar dalam Al-Qur'an?", Intent.QURANIC_INFORMATION),
        ("Apakah utang berbunga dibolehkan dalam Islam?", Intent.ISLAMIC_GUIDANCE),
        ("Bagaimana membuat anggaran keuangan bulanan?", Intent.PRACTICAL_LIFE_GUIDANCE),
        ("Jelaskan recursion di Python", Intent.GENERAL_INFORMATION),
        ("Berapa harga Bitcoin hari ini?", Intent.OUT_OF_SCOPE),
        ("Kenapa hidupku terasa selalu tertinggal?", Intent.EMOTIONAL_REFLECTION),
    ],
)
def test_classify_intent_covers_supported_routes(query, intent):
    assert classify_intent(query).primary_intent == intent


def test_classify_intent_prefers_emotional_need_in_mixed_query():
    decision = classify_intent("Aku cemas setelah kehilangan pekerjaan")

    assert decision.primary_intent == Intent.EMOTIONAL_REFLECTION
    assert decision.secondary_intents
    assert decision.requires_quran


def test_classify_intent_marks_ambiguous_request_for_clarification():
    decision = classify_intent("Tolong bantu aku")

    assert decision.needs_clarification


def test_distress_terms_add_theme_hints():
    query, themes = enrich_query("Aku cemas menghadapi masa depan")
    assert "kecemasan" in themes
    assert "takut_masa_depan" in themes
    assert "Tema refleksi" in query


def test_unmatched_query_is_not_rewritten():
    query, themes = enrich_query("Harga Bitcoin hari ini")
    assert query == "Harga Bitcoin hari ini"
    assert themes == []


def test_generic_tomorrow_does_not_trigger_future_anxiety_theme():
    query, themes = enrich_query("Berapa harga Bitcoin besok?")
    assert query == "Berapa harga Bitcoin besok?"
    assert themes == []
    assert is_out_of_scope(query)


def test_financial_context_with_expressed_distress_remains_reflective():
    assert not is_out_of_scope("Aku cemas karena harga Bitcoin jatuh")


def test_emptiness_terms_add_theme_hint():
    query, themes = enrich_query("Aku merasa hampa dan kosong")
    assert "kehampaan" in themes
    assert "Tema refleksi" in query


def test_query_understanding_returns_non_diagnostic_metadata():
    result = understand_query("  Aku CEMAS soal masa depan  ")
    assert result.normalized_query == "aku cemas soal masa depan"
    assert "kecemasan" in result.possible_themes
    assert "takut_masa_depan" in result.possible_themes
    assert "ketenangan" in result.retrieval_hints
    assert "Konsep terkait" in enrich_query("Aku cemas")[0]


def test_mental_health_taxonomy_terms_are_retrievable():
    result = understand_query("Aku burnout dan merasa ditolak setelah kehilangan pekerjaan")
    assert "burnout" in result.possible_themes
    assert "penolakan" in result.possible_themes
    assert "tekanan_finansial_karier" in result.possible_themes
