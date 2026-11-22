"""Response builders for paths that do not use the LLM.

Every builder returns a draft without evidence; the pipeline passes drafts
through :class:`~app.rag.citation_validator.CitationValidator` so evidence is
always copied from retrieved rows, never from a model.
"""

from typing import Any

from app.models.chat import QalbuResponse, QuranReference
from app.models.quran import QuranDocument
from app.rag import messages
from app.rag.query_processing import Intent, IntentDecision
from app.safety.guardrails import SafetyDecision, SafetyLevel


def crisis_response(decision: SafetyDecision) -> QalbuResponse:
    return QalbuResponse(
        answer=decision.response or messages.IMMEDIATE_DANGER_FALLBACK,
        references=[],
        safety_note=messages.IMMEDIATE_DANGER_SAFETY_NOTE,
        mode="crisis",
        reason_code="immediate_danger",
    )


def crisis_event(
    decision: SafetyDecision,
    crisis_line: str | None,
    crisis_line_label: str,
) -> dict[str, Any]:
    return {
        "message": decision.response or messages.IMMEDIATE_DANGER_FALLBACK,
        "crisis_line": crisis_line_label,
        "tel": f"tel:{crisis_line}" if crisis_line else None,
    }


def scope_limit_response(intent: IntentDecision | None = None) -> QalbuResponse:
    if intent and intent.needs_clarification:
        return QalbuResponse(
            answer=messages.NEEDS_CLARIFICATION,
            references=[],
            mode="scope_limit",
            reason_code="needs_clarification",
        )
    if intent and intent.primary_intent != Intent.OUT_OF_SCOPE:
        return QalbuResponse(
            answer=messages.SCOPE_LIMIT,
            references=[],
            mode="scope_limit",
            reason_code="scope_limit",
        )
    return QalbuResponse(
        answer=messages.OUT_OF_SCOPE,
        references=[],
        safety_note=None,
        mode="scope_limit",
        reason_code="out_of_scope",
    )


def no_context_response() -> QalbuResponse:
    return QalbuResponse(
        answer=messages.NO_RELEVANT_CONTEXT,
        references=[],
        safety_note=None,
        mode="sources_only",
        reason_code="no_relevant_context",
    )


def translation_unavailable_response(documents: list[QuranDocument]) -> QalbuResponse:
    return QalbuResponse(
        answer=messages.TRANSLATION_UNAVAILABLE,
        references=_references(documents),
        safety_note=messages.TRANSLATION_UNAVAILABLE_NOTE,
        mode="sources_only",
        reason_code="verified_translation_unavailable",
    )


def brief_translation_unavailable_response(
    documents: list[QuranDocument],
) -> QalbuResponse:
    return QalbuResponse(
        answer=messages.TRANSLATION_UNAVAILABLE_BRIEF,
        references=_references(documents),
        mode="sources_only",
        reason_code="verified_translation_unavailable",
    )


def sources_only_response(documents: list[QuranDocument]) -> QalbuResponse:
    return QalbuResponse(
        answer=messages.SOURCES_ONLY,
        references=_references(documents),
        mode="sources_only",
        reason_code="generation_unavailable",
    )


def with_human_support_note(
    response: QalbuResponse, safety_level: SafetyLevel
) -> QalbuResponse:
    """Append a human-support note only for high distress."""
    if safety_level != SafetyLevel.HIGH_DISTRESS:
        return response
    note = (
        f"{response.safety_note} {messages.HUMAN_SUPPORT_NOTE}"
        if response.safety_note
        else messages.HUMAN_SUPPORT_NOTE
    )
    return response.model_copy(update={"safety_note": note})


def has_no_verified_translation(documents: list[QuranDocument]) -> bool:
    """True when every retrieved document is community data without translation."""
    return bool(documents) and all(
        not document.translation and bool(document.metadata.get("unverified_community_source"))
        for document in documents
    )


def _references(documents: list[QuranDocument]) -> list[QuranReference]:
    return [QuranReference(parent_id=document.id) for document in documents]
