from app.rag.query_processing import enrich_query


def test_distress_terms_add_theme_hints():
    query, themes = enrich_query("Aku cemas menghadapi masa depan")
    assert "kecemasan" in themes
    assert "takut_masa_depan" in themes
    assert "Tema refleksi" in query


def test_unmatched_query_is_not_rewritten():
    query, themes = enrich_query("Harga Bitcoin hari ini")
    assert query == "Harga Bitcoin hari ini"
    assert themes == []


def test_emptiness_terms_add_theme_hint():
    query, themes = enrich_query("Aku merasa hampa dan kosong")
    assert "kehampaan" in themes
    assert "Tema refleksi" in query
