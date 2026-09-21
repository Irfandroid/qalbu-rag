from app.models.chat import QalbuResponse, QuranReference
from app.rag.citation_validator import CitationValidator
from tests.conftest import document


def test_valid_citation_kept():
    response = QalbuResponse(
        answer="x",
        references=[
            QuranReference(
                parent_id="al-baqarah-286",
                surah_number=2,
                surah_name="Al-Baqarah",
                ayah_start=286,
                ayah_end=286,
            )
        ],
    )
    assert len(CitationValidator().validate(response, [document()]).references) == 1


def test_hallucinated_citation_rejected():
    response = QalbuResponse(
        answer="x",
        references=[
            QuranReference(
                parent_id="unknown",
                surah_number=2,
                surah_name="Al-Baqarah",
                ayah_start=999,
                ayah_end=999,
            )
        ],
    )
    assert not CitationValidator().validate(response, [document()]).references


def test_parent_id_only_citation_is_completed_from_retrieved_parent():
    response = QalbuResponse(
        answer="x",
        references=[QuranReference(parent_id="al-baqarah-286")],
    )
    reference = CitationValidator().validate(response, [document()]).references[0]
    assert reference.surah_name == "Al-Baqarah"
    assert reference.ayah_start == 286


def test_valid_citation_returns_exact_parent_evidence():
    source = document().model_copy(update={"arabic_text": "لَا يُكَلِّفُ"})
    response = QalbuResponse(
        answer="x",
        references=[QuranReference(parent_id="al-baqarah-286")],
    )
    evidence = CitationValidator().validate(response, [source]).evidence[0]
    assert evidence.arabic_text == "لَا يُكَلِّفُ"
    assert evidence.parent_id == "al-baqarah-286"


def test_community_source_adds_provenance_note():
    source = document().model_copy(update={"metadata": {"unverified_community_source": True}})
    response = QalbuResponse(
        answer="x",
        references=[QuranReference(parent_id="al-baqarah-286")],
    )
    assert "dataset komunitas" in (
        CitationValidator().validate(response, [source]).safety_note or ""
    )


def test_community_tafsir_adds_provenance_note():
    source = document().model_copy(
        update={"metadata": {"tafsir_unverified_community_source": True}}
    )
    response = QalbuResponse(
        answer="x",
        references=[QuranReference(parent_id="al-baqarah-286")],
    )

    assert "dataset komunitas" in (
        CitationValidator().validate(response, [source]).safety_note or ""
    )
