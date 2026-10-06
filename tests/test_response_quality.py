from app.models.chat import QalbuResponse, QuranReference
from app.models.quran import QuranDocument
from app.rag.response_quality import (
    assess_contextual_response,
    build_repair_query,
)


def source() -> QuranDocument:
    return QuranDocument(
        id="qalbu-seed-013-028",
        surah_number=13,
        surah_name="Ar-Ra'd",
        ayah_start=28,
        ayah_end=28,
        translation="Hearts are assured by the remembrance of Allah.",
        tafsir="Tasbih, tahmid, recitation and listening are forms of remembrance.",
        source={"quran": "Kemenag"},
    )


def test_generic_answer_fails_context_and_tafsir_gates():
    response = QalbuResponse(
        answer="Mengingat Allah menenangkan hati.",
        references=[QuranReference(parent_id="qalbu-seed-013-028")],
    )

    report = assess_contextual_response(
        "Aku merasa hampa", response, [source()], max_tokens=72
    )

    assert not report.passed
    assert "missing_context_ack" in report.issues
    assert "missing_tafsir_attribution" in report.issues
    assert "missing_empathy" in report.issues
    assert "missing_grounding_bridge" in report.issues


def test_contextual_grounded_answer_passes():
    response = QalbuResponse(
        answer=(
            "Rasa hampa itu bisa terasa berat. Ayat ini mengajak hati mengingat Allah. "
            "Dalam tafsir yang tersedia, zikir mencakup tasbih dan tahmid."
        ),
        references=[QuranReference(parent_id="qalbu-seed-013-028")],
    )

    report = assess_contextual_response(
        "Aku merasa hampa", response, [source()], max_tokens=72
    )

    assert report.passed


def test_repair_query_contains_failures_without_fixed_answer():
    response = QalbuResponse(answer="Jawaban generik", references=[])
    report = assess_contextual_response(
        "Aku merasa hampa", response, [source()], max_tokens=72
    )

    repair = build_repair_query("Current user message: Aku merasa hampa", response, report)

    assert "missing_context_ack" in repair
    assert "Tulis ulang dari nol" in repair
    assert "Aku mendengar kamu sedang merasa hampa" not in repair


def test_rejects_embedded_arabic_or_source_identifier():
    response = QalbuResponse(
        answer=(
            "Rasa hampa terkait Ar-Ra'd dan teks أَلَا. "
            "Dalam tafsir yang tersedia, zikir menenteramkan hati."
        ),
        references=[QuranReference(parent_id="qalbu-seed-013-028")],
    )

    report = assess_contextual_response(
        "Aku merasa hampa", response, [source()], max_tokens=72
    )

    assert "embedded_arabic_quote" in report.issues
    assert "embedded_source_identifier" in report.issues


def test_rejects_model_authored_quotation():
    response = QalbuResponse(
        answer=(
            "Rasa hampa terkait ayat ini: 'kutipan buatan model'. "
            "Dalam tafsir yang tersedia, zikir menenteramkan hati."
        ),
        references=[QuranReference(parent_id="qalbu-seed-013-028")],
    )

    report = assess_contextual_response(
        "Aku merasa hampa", response, [source()], max_tokens=72
    )

    assert "embedded_quotation" in report.issues


def test_rejects_empathy_without_source_grounding():
    response = QalbuResponse(
        answer=(
            "Aku memahami perasaanmu. Ayat ini mungkin membantu kamu menjalani hari."
        ),
        references=[QuranReference(parent_id="qalbu-seed-013-028")],
    )

    report = assess_contextual_response(
        "Aku merasa hampa", response, [source()], max_tokens=72
    )

    assert "missing_source_anchor" in report.issues


def test_rejects_dismissive_tone():
    response = QalbuResponse(
        answer=(
            "Kamu harus bersyukur. Ayat ini mengingatkan hati. "
            "Dalam tafsir yang tersedia, zikir mencakup tasbih dan tahmid."
        ),
        references=[QuranReference(parent_id="qalbu-seed-013-028")],
    )

    report = assess_contextual_response(
        "Aku merasa hampa", response, [source()], max_tokens=72
    )

    assert "dismissive_or_preachy" in report.issues
