import logging
import time
from collections.abc import AsyncIterator
from hashlib import sha256
from typing import Any

from app.core.cache import rag_response_cache
from app.llm.base import LLMProvider
from app.models.chat import ChatRequest, QalbuResponse, QuranReference
from app.models.quran import QuranDocument
from app.rag.citation_validator import CitationValidator
from app.rag.context_builder import build_context
from app.rag.curated_fallback import CuratedFallbackRetriever
from app.rag.parent_retriever import ParentRetriever
from app.rag.response_quality import (
    assess_contextual_response,
    build_curated_safe_response,
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
        parents: ParentRetriever,
        llm: LLMProvider,
        validator: CitationValidator,
        cache_version: str = "sample-v1",
        profile: str = "local",
        crisis_line: str | None = None,
        crisis_line_label: str = "Layanan darurat setempat",
    ) -> None:
        self.safety, self.retriever, self.parents, self.llm, self.validator = (
            safety,
            retriever,
            parents,
            llm,
            validator,
        )
        self.cache_version = f"{cache_version}:grounded-v9"
        self.profile = profile
        self.crisis_line = crisis_line
        self.crisis_line_label = crisis_line_label

    async def retrieve(self, query: str, request_id: str):
        children = await self.retriever.search(query)
        vector_documents = await self.parents.get_parents(children)
        curated = await CuratedFallbackRetriever(self.parents.repository).search(query)
        if curated:
            logger.info("curated_hybrid_hit request_id=%s", request_id)
            # Exact, reviewed intent matches are safer than an additional
            # semantically similar vector result for a high-stakes reflection.
            candidates = curated
        else:
            candidates = vector_documents
        documents = [
            document
            for document in candidates
            if not bool(document.metadata.get("accusatory", False))
        ][: self.retriever.parent_k]
        return children, documents

    async def ask(self, query: str, request_id: str) -> QalbuResponse:
        decision = self.safety.check(query)
        if decision.level == SafetyLevel.IMMEDIATE_DANGER:
            return QalbuResponse(
                answer=decision.response or "Please seek immediate help.",
                references=[],
                safety_note="Immediate support recommended.",
            )
        started = time.perf_counter()
        cache_key = sha256(f"{self.cache_version}\0{query.strip().lower()}".encode()).hexdigest()
        cached = rag_response_cache.get(cache_key)
        if cached is not None:
            logger.info("rag_cache_hit request_id=%s", request_id)
            return QalbuResponse.model_validate(cached)
        children, documents = await self.retrieve(query, request_id)
        if not documents:
            return QalbuResponse(
                answer=(
                    "Konteks sumber yang tersedia belum cukup untuk merespons "
                    "dengan bertanggung jawab."
                ),
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
            return self.validator.validate(draft, documents)
        validated = await self._generate_validated(
            user_query=query,
            generation_query=query,
            documents=documents,
            max_tokens=120,
            request_id=request_id,
        )
        if validated is None:
            logger.warning("ungrounded_llm_response request_id=%s", request_id)
            return QalbuResponse(
                answer=(
                    "Aku belum bisa memberi refleksi yang terikat pada sumber karena "
                    "referensi jawaban tidak dapat diverifikasi."
                ),
                references=[],
                safety_note=None,
            )
        logger.info(
            "rag_complete request_id=%s chunks=%s parents=%s latency_ms=%s citations=%s",
            request_id,
            len(children),
            [doc.id for doc in documents],
            round((time.perf_counter() - started) * 1000),
            len(validated.references),
        )
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
                    "message": decision.response,
                    "crisis_line": self.crisis_line_label,
                    "tel": f"tel:{self.crisis_line}" if self.crisis_line else None,
                },
            )
            yield "done", self._done_payload(started, request_id)
            return

        retrieval_started = time.perf_counter()
        _children, documents = await self.retrieve(request.message, request_id)
        retrieval_ms = round((time.perf_counter() - retrieval_started) * 1000, 2)
        if not documents:
            fallback = QalbuResponse(
                answer=(
                    "Aku belum menemukan ayat yang cukup relevan. "
                    "Coba ceritakan kembali dengan kata yang lebih spesifik."
                ),
                references=[],
            )
            yield "response", fallback.model_dump(mode="json")
            yield "done", self._done_payload(started, request_id, retrieval_ms=retrieval_ms)
            return

        if request.lang == "id" and self._missing_verified_translation(documents[:3]):
            unavailable = QalbuResponse(
                answer=(
                    "Terjemahan Indonesia terverifikasi belum tersedia. "
                    "Qalbu tidak akan menerjemahkan atau membuat refleksi dari model."
                ),
                references=[QuranReference(parent_id=document.id) for document in documents[:3]],
            )
            unavailable_response = self.validator.validate(unavailable, documents[:3])
            yield "response", unavailable_response.model_dump(mode="json")
            yield "done", self._done_payload(started, request_id, retrieval_ms=retrieval_ms)
            return

        generation_started = time.perf_counter()
        try:
            language = "Bahasa Indonesia" if request.lang == "id" else "English"
            history = "\n".join(f"{turn.role}: {turn.content}" for turn in request.history[-3:])
            generation_query = (
                f"Output language: {language}. Tone: {request.tone}. "
                f"Maximum length: {request.max_tokens} tokens.\n"
                f"Recent history:\n{history or '[none]'}\n"
                f"Current user message: {request.message}"
            )
            validated = await self._generate_validated(
                user_query=request.message,
                generation_query=generation_query,
                documents=documents[:3],
                max_tokens=request.max_tokens,
                request_id=request_id,
            )
        except Exception:
            logger.exception("stream_generation_failed request_id=%s", request_id)
            yield "reflection_unavailable", {"reason": "generator_down"}
            yield "done", self._done_payload(started, request_id, retrieval_ms=retrieval_ms)
            return

        generation_ms = round((time.perf_counter() - generation_started) * 1000, 2)
        if validated is None:
            yield (
                "reflection_unavailable",
                {
                    "reason": "validation_failed",
                    "message": (
                        "Aku belum bisa menyusun refleksi yang cukup relevan dan "
                        "terikat pada sumber. Coba ceritakan dengan sedikit lebih spesifik."
                    ),
                },
            )
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
        context = build_context(documents)
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
            fallback = build_curated_safe_response(user_query, documents)
            if fallback is not None:
                curated = self.validator.validate(fallback, documents)
                curated_report = assess_contextual_response(
                    user_query,
                    curated,
                    documents,
                    max_tokens=max_tokens,
                )
                if curated_report.passed:
                    logger.warning(
                        "curated_response_fallback request_id=%s parent_id=%s",
                        request_id,
                        curated.references[0].parent_id,
                    )
                    return curated
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
    def _reference_label(document) -> str:
        ayah = (
            str(document.ayah_start)
            if document.ayah_start == document.ayah_end
            else f"{document.ayah_start}-{document.ayah_end}"
        )
        return f"{document.surah_name} {document.surah_number}:{ayah}"

    @staticmethod
    def _missing_verified_translation(documents: list[QuranDocument]) -> bool:
        return bool(documents) and all(
            not document.translation and bool(document.metadata.get("unverified_community_source"))
            for document in documents
        )
