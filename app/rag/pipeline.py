"""Orchestration for the Qalbu reflection path.

Order is fixed and safety-critical: safety gate -> intent routing -> retrieval ->
grounded generation -> citation/quality validation -> fallback. No user prompt
reaches an external provider before the safety gate and intent router agree.
"""

import logging
import time
from collections.abc import AsyncIterator
from hashlib import sha256
from typing import Any

from app.core.cache import rag_response_cache
from app.models.chat import ChatRequest, QalbuResponse
from app.models.quran import QuranDocument
from app.models.rag import RetrievalResult
from app.providers.llm.base import LLMProvider
from app.rag import responses
from app.rag.citation_validator import CitationValidator
from app.rag.context_builder import build_context
from app.rag.query_processing import IntentDecision, classify_intent
from app.rag.response_quality import assess_contextual_response, build_repair_query
from app.rag.retriever import QuranRetriever
from app.safety.guardrails import SafetyGuardrails, SafetyLevel

logger = logging.getLogger(__name__)

# The SSE path deliberately keeps the context small so the first useful answer
# arrives quickly; the non-streaming path may use every retrieved parent.
MAX_GENERATION_SOURCES = 3
# One initial draft plus one repair attempt driven by concrete quality issues.
MAX_GENERATION_ATTEMPTS = 2


class QalbuRAG:
    def __init__(
        self,
        safety: SafetyGuardrails,
        retriever: QuranRetriever,
        llm: LLMProvider,
        validator: CitationValidator,
        cache_version: str = "sample-v1",
        profile: str = "local",
        crisis_line: str | None = None,
        crisis_line_label: str = "Layanan darurat setempat",
        max_context_tokens: int = 1800,
    ) -> None:
        self.safety = safety
        self.retriever = retriever
        self.llm = llm
        self.validator = validator
        self.cache_version = f"{cache_version}:mvp-v1"
        self.profile = profile
        self.crisis_line = crisis_line
        self.crisis_line_label = crisis_line_label
        self.max_context_tokens = max_context_tokens
        self.max_answer_tokens = 72

    async def retrieve(
        self, query: str, request_id: str
    ) -> tuple[list[RetrievalResult], list[QuranDocument]]:
        """Retrieve parents for callers that only need search results."""
        return await self._retrieve(query, request_id, classify_intent(query))

    async def ask(self, query: str, request_id: str) -> QalbuResponse:
        decision = self.safety.check(query)
        if decision.level == SafetyLevel.IMMEDIATE_DANGER:
            return responses.crisis_response(decision)

        intent = classify_intent(query)
        if not intent.requires_quran:
            return responses.scope_limit_response(intent)

        cache_key = self._cache_key(query)
        cached = rag_response_cache.get(cache_key)
        if cached is not None:
            logger.info("rag_cache_hit request_id=%s", request_id)
            return QalbuResponse.model_validate(cached)

        started = time.perf_counter()
        matches, documents = await self._retrieve(query, request_id, intent)
        fallback = self._fallback_before_generation(documents, decision.level)
        if fallback is not None:
            return fallback

        try:
            validated = await self._generate_validated(
                user_query=query,
                generation_query=f"Pesan pengguna: {query}",
                documents=documents,
                max_tokens=self.max_answer_tokens,
                request_id=request_id,
            )
        except Exception:
            logger.exception("generation_failed_sources_only request_id=%s", request_id)
            return self._sources_only(documents, decision.level)

        if validated is None:
            logger.warning("ungrounded_llm_response request_id=%s", request_id)
            return self._sources_only(documents, decision.level)

        logger.info(
            "rag_complete request_id=%s matches=%s parents=%s latency_ms=%s citations=%s",
            request_id,
            len(matches),
            [document.id for document in documents],
            self._elapsed_ms(started),
            len(validated.references),
        )
        validated = self._with_distress_note(validated, decision.level)
        rag_response_cache.set(cache_key, validated.model_dump())
        return validated

    async def stream_events(
        self, request: ChatRequest, request_id: str
    ) -> AsyncIterator[tuple[str, dict[str, Any]]]:
        """Emit only validated responses; retrieval candidates never reach the UI."""
        started = time.perf_counter()
        decision = self.safety.check(request.message)
        if decision.level == SafetyLevel.IMMEDIATE_DANGER:
            yield (
                "crisis",
                responses.crisis_event(
                    decision, self.crisis_line, self.crisis_line_label
                ),
            )
            yield "done", self._done_payload(started, request_id)
            return

        intent = classify_intent(request.message)
        if not intent.requires_quran:
            yield "response", responses.scope_limit_response(intent).model_dump(mode="json")
            yield "done", self._done_payload(started, request_id)
            return

        retrieval_started = time.perf_counter()
        _matches, documents = await self._retrieve(request.message, request_id, intent)
        retrieval_ms = self._elapsed_ms(retrieval_started)

        if not documents:
            yield "response", responses.no_context_response().model_dump(mode="json")
            yield "done", self._done_payload(started, request_id, retrieval_ms=retrieval_ms)
            return

        sources = documents[:MAX_GENERATION_SOURCES]
        if responses.has_no_verified_translation(sources):
            fallback = self._brief_translation_unavailable(sources, decision.level)
            yield "response", fallback.model_dump(mode="json")
            yield "done", self._done_payload(started, request_id, retrieval_ms=retrieval_ms)
            return

        generation_started = time.perf_counter()
        try:
            validated = await self._generate_validated(
                user_query=request.message,
                generation_query=f"Pesan pengguna: {request.message}",
                documents=sources,
                max_tokens=self.max_answer_tokens,
                request_id=request_id,
            )
        except Exception:
            logger.exception("stream_generation_failed request_id=%s", request_id)
            yield "response", self._sources_only(sources, decision.level).model_dump(mode="json")
            yield "done", self._done_payload(started, request_id, retrieval_ms=retrieval_ms)
            return

        generation_ms = self._elapsed_ms(generation_started)
        if validated is None:
            yield "response", self._sources_only(sources, decision.level).model_dump(mode="json")
            yield (
                "done",
                self._done_payload(
                    started,
                    request_id,
                    retrieval_ms=retrieval_ms,
                    generation_ms=generation_ms,
                ),
            )
            return

        validated = self._with_distress_note(validated, decision.level)
        yield "response", validated.model_dump(mode="json")
        yield (
            "done",
            self._done_payload(
                started,
                request_id,
                retrieval_ms=retrieval_ms,
                generation_ms=generation_ms,
            ),
        )

    async def _retrieve(
        self,
        query: str,
        request_id: str,
        intent: IntentDecision,
    ) -> tuple[list[RetrievalResult], list[QuranDocument]]:
        if not intent.requires_quran:
            return [], []
        matches = await self.retriever.search(query, request_id)
        candidates = await self.retriever.repository.get_documents(
            [result.parent_id for result in matches]
        )
        documents = [
            document
            for document in candidates
            if not bool(document.metadata.get("accusatory", False))
        ][: self.retriever.parent_k]
        return matches, documents

    async def _generate_validated(
        self,
        *,
        user_query: str,
        generation_query: str,
        documents: list[QuranDocument],
        max_tokens: int,
        request_id: str,
    ) -> QalbuResponse | None:
        """Generate dynamically, then retry once with concrete quality failures."""
        context = build_context(documents, self.max_context_tokens)
        prompt = generation_query
        for attempt in range(MAX_GENERATION_ATTEMPTS):
            response = await self.llm.generate(prompt, context, max_tokens)
            response = response.model_copy(update={"safety_note": None})
            validated = self.validator.validate(response, documents)
            report = assess_contextual_response(
                user_query,
                validated,
                documents,
                max_tokens=max_tokens,
            )
            if report.passed:
                return validated
            logger.warning(
                "response_quality_failed request_id=%s attempt=%s issues=%s",
                request_id,
                attempt + 1,
                report.issues,
            )
            prompt = build_repair_query(generation_query, validated, report)
        return None

    def _fallback_before_generation(
        self,
        documents: list[QuranDocument],
        safety_level: SafetyLevel,
    ) -> QalbuResponse | None:
        """Return a non-generated response when retrieval cannot ground an answer."""
        if not documents:
            return responses.no_context_response()
        if responses.has_no_verified_translation(documents):
            draft = responses.translation_unavailable_response(documents)
            return self._with_distress_note(
                self.validator.validate(draft, documents), safety_level
            )
        return None

    def _sources_only(
        self,
        documents: list[QuranDocument],
        safety_level: SafetyLevel,
    ) -> QalbuResponse:
        draft = responses.sources_only_response(documents)
        return self._with_distress_note(
            self.validator.validate(draft, documents), safety_level
        )

    def _brief_translation_unavailable(
        self,
        documents: list[QuranDocument],
        safety_level: SafetyLevel,
    ) -> QalbuResponse:
        draft = responses.brief_translation_unavailable_response(documents)
        return self._with_distress_note(
            self.validator.validate(draft, documents), safety_level
        )

    def _cache_key(self, query: str) -> str:
        versioned_query = f"{self.cache_version}\0{query.strip().lower()}"
        return sha256(versioned_query.encode()).hexdigest()

    def _done_payload(
        self,
        started: float,
        request_id: str,
        retrieval_ms: float | None = None,
        generation_ms: float | None = None,
    ) -> dict[str, Any]:
        return {
            "timings": {
                "total_ms": self._elapsed_ms(started),
                "retrieval_ms": retrieval_ms,
                "generation_ms": generation_ms,
            },
            "profile": self.profile,
            "request_id": request_id,
        }

    @staticmethod
    def _elapsed_ms(started: float) -> float:
        return round((time.perf_counter() - started) * 1000, 2)

    @staticmethod
    def _with_distress_note(
        response: QalbuResponse,
        safety_level: SafetyLevel,
    ) -> QalbuResponse:
        return responses.with_human_support_note(response, safety_level)
