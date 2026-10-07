from app.rag.query_processing import enrich_query, is_out_of_scope, understand_query


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
