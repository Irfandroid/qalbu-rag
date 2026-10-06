import logging
import time
from collections.abc import AsyncIterator
from hashlib import sha256
from typing import Any

from app.core.cache import rag_response_cache
from app.models.chat import ChatRequest, QalbuResponse, QuranReference
from app.models.quran import QuranDocument
from app.providers.llm.base import LLMProvider
from app.rag.citation_validator import CitationValidator
from app.rag.context_builder import build_context
from app.rag.query_processing import is_out_of_scope
from app.rag.response_quality import (
    assess_contextual_response,
    build_repair_query,
)
from app.rag.retriever import QuranRetriever
from app.safety.guardrails import SafetyGuardrails, SafetyLevel

logger = logging.getLogger(__name__)


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

    async def retrieve(self, query: str, request_id: str):
        if is_out_of_scope(query):
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

    async def ask(self, query: str, request_id: str) -> QalbuResponse:
        decision = self.safety.check(query)
        if decision.level == SafetyLevel.IMMEDIATE_DANGER:
            return QalbuResponse(
                answer=decision.response
                or "Jika ada bahaya segera, hubungi layanan darurat setempat.",
                references=[],
                safety_note="Dukungan segera disarankan.",
            )
        if is_out_of_scope(query):
            return self._out_of_scope_response()
        started = time.perf_counter()
        cache_key = sha256(f"{self.cache_version}\0{query.strip().lower()}".encode()).hexdigest()
        cached = rag_response_cache.get(cache_key)
        if cached is not None:
            logger.info("rag_cache_hit request_id=%s", request_id)
            return QalbuResponse.model_validate(cached)
        matches, documents = await self.retrieve(query, request_id)
        if not documents:
            return QalbuResponse(
                answer=self._no_context_response(),
                references=[],
                safety_note=None,
            )
        if self._missing_verified_translation(documents):
            draft = QalbuResponse(
                answer=(
                    "Terjemahan Indonesia terverifikasi belum tersedia pada sumber aktif. "
                    "Teks Arab dan tafsir sumber tetap ditampilkan tanpa dibuatkan terjemahan "
                    "atau refleksi oleh model."
                ),
                references=[QuranReference(parent_id=document.id) for document in documents],
                safety_note="Dataset aktif adalah sumber komunitas, bukan sumber resmi Kemenag.",
            )
            return self._with_distress_note(
                self.validator.validate(draft, documents), decision.level
            )
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
            return self._sources_only_response(documents, decision.level)
        if validated is None:
            logger.warning("ungrounded_llm_response request_id=%s", request_id)
            return self._sources_only_response(documents, decision.level)
        logger.info(
            "rag_complete request_id=%s matches=%s parents=%s latency_ms=%s citations=%s",
            request_id,
            len(matches),
            [doc.id for doc in documents],
            round((time.perf_counter() - started) * 1000),
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
                {
                    "message": decision.response
                    or "Jika ada bahaya segera, hubungi layanan darurat setempat.",
                    "crisis_line": self.crisis_line_label,
                    "tel": f"tel:{self.crisis_line}" if self.crisis_line else None,
                },
            )
            yield "done", self._done_payload(started, request_id)
            return

        if is_out_of_scope(request.message):
            yield "response", self._out_of_scope_response().model_dump(mode="json")
            yield "done", self._done_payload(started, request_id)
            return

        retrieval_started = time.perf_counter()
        _matches, documents = await self.retrieve(request.message, request_id)
        retrieval_ms = round((time.perf_counter() - retrieval_started) * 1000, 2)
        if not documents:
            fallback = QalbuResponse(
                answer=self._no_context_response(),
                references=[],
            )
            yield "response", fallback.model_dump(mode="json")
            yield "done", self._done_payload(started, request_id, retrieval_ms=retrieval_ms)
            return

        if self._missing_verified_translation(documents[:3]):
            unavailable = QalbuResponse(
                answer=(
                    "Terjemahan Indonesia terverifikasi belum tersedia. "
                    "Qalbu tidak akan menerjemahkan atau membuat refleksi dari model."
                ),
                references=[QuranReference(parent_id=document.id) for document in documents[:3]],
            )
            unavailable_response = self._with_distress_note(
                self.validator.validate(unavailable, documents[:3]), decision.level
            )
            yield "response", unavailable_response.model_dump(mode="json")
            yield "done", self._done_payload(started, request_id, retrieval_ms=retrieval_ms)
            return

        generation_started = time.perf_counter()
        try:
            generation_query = f"Pesan pengguna: {request.message}"
            validated = await self._generate_validated(
                user_query=request.message,
                generation_query=generation_query,
                documents=documents[:3],
                max_tokens=self.max_answer_tokens,
                request_id=request_id,
            )
        except Exception:
            logger.exception("stream_generation_failed request_id=%s", request_id)
            fallback = self._sources_only_response(documents[:3], decision.level)
            yield "response", fallback.model_dump(mode="json")
            yield "done", self._done_payload(started, request_id, retrieval_ms=retrieval_ms)
            return

        generation_ms = round((time.perf_counter() - generation_started) * 1000, 2)
        if validated is None:
            fallback = self._sources_only_response(documents[:3], decision.level)
            yield "response", fallback.model_dump(mode="json")
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
        for attempt in range(2):
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

    def _done_payload(
        self,
        started: float,
        request_id: str,
        retrieval_ms: float | None = None,
        generation_ms: float | None = None,
    ) -> dict[str, Any]:
        return {
            "timings": {
                "total_ms": round((time.perf_counter() - started) * 1000, 2),
                "retrieval_ms": retrieval_ms,
                "generation_ms": generation_ms,
            },
            "profile": self.profile,
            "request_id": request_id,
        }

    @staticmethod
    def _out_of_scope_response() -> QalbuResponse:
        return QalbuResponse(
            answer=(
                "Pertanyaan itu berada di luar ruang refleksi Qalbu. "
                "Ceritakan perasaan atau keadaan yang sedang kamu hadapi agar Qalbu "
                "dapat mencari sumber Al-Qur'an yang relevan."
            ),
            references=[],
            safety_note=None,
        )

    @staticmethod
    def _no_context_response() -> str:
        return (
            "Aku belum menemukan ayat yang cukup relevan. "
            "Coba ceritakan kembali dengan kata yang lebih spesifik."
        )

    def _sources_only_response(
        self,
        documents: list[QuranDocument],
        safety_level: SafetyLevel,
    ) -> QalbuResponse:
        draft = QalbuResponse(
            answer=(
                "Refleksi AI sedang tidak tersedia saat ini. Sumber Al-Qur'an hasil pencarian "
                "tetap ditampilkan agar kamu dapat membacanya dan menilainya sendiri dengan tenang."
            ),
            references=[QuranReference(parent_id=document.id) for document in documents],
        )
        return self._with_distress_note(
            self.validator.validate(draft, documents), safety_level
        )

    @staticmethod
    def _with_distress_note(
        response: QalbuResponse,
        safety_level: SafetyLevel,
    ) -> QalbuResponse:
        if safety_level != SafetyLevel.HIGH_DISTRESS:
            return response
        support = (
            "Jika keadaan terasa makin berat, hubungi orang tepercaya atau tenaga "
            "kesehatan mental yang dapat mendampingi secara langsung."
        )
        note = f"{response.safety_note} {support}" if response.safety_note else support
        return response.model_copy(update={"safety_note": note})

    @staticmethod
    def _missing_verified_translation(documents: list[QuranDocument]) -> bool:
        return bool(documents) and all(
            not document.translation and bool(document.metadata.get("unverified_community_source"))
            for document in documents
        )
