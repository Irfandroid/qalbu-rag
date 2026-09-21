from app.llm.ollama import OllamaProvider
from app.models.chat import QalbuResponse, QuranReference


def test_missing_reference_is_attached_for_one_unambiguous_parent():
    response = QalbuResponse(answer="Refleksi", references=[])
    context = """<retrieved_context>
PARENT_ID: quran-com-en-013-028
</retrieved_context>"""

    recovered = OllamaProvider._attach_single_context_reference(response, context)

    assert [item.parent_id for item in recovered.references] == ["quran-com-en-013-028"]


def test_missing_references_are_not_synthesized_for_multiple_parents():
    response = QalbuResponse(answer="Refleksi", references=[])
    context = "PARENT_ID: first\nPARENT_ID: second"

    recovered = OllamaProvider._attach_single_context_reference(response, context)

    assert recovered.references == []


def test_existing_model_references_are_not_replaced():
    response = QalbuResponse(
        answer="Refleksi",
        references=[QuranReference(parent_id="quran-com-en-013-028")],
    )

    recovered = OllamaProvider._attach_single_context_reference(
        response, "PARENT_ID: quran-com-en-051-056"
    )

    assert recovered.references == response.references
