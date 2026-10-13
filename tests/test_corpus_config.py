from app.core.config import Settings


def test_qalbu_corpus_defaults_to_kemenag():
    settings = Settings(_env_file=None)
    assert settings.quran_corpus == "qalbu-kemenag-v1"


def test_qalbu_corpus_can_roll_back_to_seed(monkeypatch):
    monkeypatch.setenv("QALBU_CORPUS", "qalbu-seed-v1")
    settings = Settings(_env_file=None)
    assert settings.quran_corpus == "qalbu-seed-v1"
