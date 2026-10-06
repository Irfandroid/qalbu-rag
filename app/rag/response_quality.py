import re
from dataclasses import dataclass

from app.models.chat import QalbuResponse
from app.models.quran import QuranDocument


@dataclass(frozen=True)
class QualityReport:
    passed: bool
    issues: tuple[str, ...]


_CONTEXT_GROUPS: tuple[tuple[str, ...], ...] = (
    ("hampa", "jampa", "kosong", "kehilangan arah", "tidak bermakna", "tak bermakna"),
    ("cemas", "kecemasan", "gelisah", "takut"),
    ("sedih", "putus asa", "harapan"),
    ("ujian", "cobaan", "sulit", "kesulitan"),
    ("berat", "beban", "lelah", "gagal"),
    ("tujuan hidup", "makna hidup", "arti hidup"),
)
_UNSUPPORTED_PROMISES = (
    "pasti sembuh",
    "akan sembuh",
    "pasti hilang",
    "akan langsung hilang",
    "solusi bagi",
    "allah pasti mencintaimu",
    "semua terjadi untuk kebaikan",
    "akan merasa tidak hampa",
)
_EMPATHY_MARKERS = (
    "bisa terasa",
    "terdengar",
    "yang kamu rasakan",
    "perasaanmu",
    "perasaan ini",
    "kondisimu",
    "wajar jika",
    "aku mendengar",
    "aku memahami",
    "aku ikut prihatin",
)
_DISMISSIVE_PATTERNS = (
    "tinggal ",
    "cuma perlu",
    "hanya perlu",
    "kamu harus",
    "jangan sedih",
    "kurang iman",
    "berpikir positif saja",
)
_GROUNDING_BRIDGES = (
    "ayat ini",
    "konteks ini",
    "sumber ini",
    "dalam tafsir yang tersedia",
    "berdasarkan sumber",
)
_SOURCE_STOPWORDS = {
    "allah",
    "yang",
    "dan",
    "dengan",
    "untuk",
    "dari",
    "pada",
    "dalam",
    "tidak",
    "akan",
    "hanya",
    "sesungguhnya",
    "mereka",
    "orang",
    "this",
    "that",
    "with",
    "from",
    "when",
    "their",
    "your",
}


def _meaningful_tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-zA-ZÀ-ÿ]+", value.casefold())
        if len(token) >= 4 and token not in _SOURCE_STOPWORDS
    }


def _has_source_anchor(answer: str, documents: list[QuranDocument]) -> bool:
    answer_tokens = _meaningful_tokens(answer)
    for document in documents:
        source_text = " ".join(
            [document.translation or "", document.tafsir or "", *document.themes]
        )
        if answer_tokens & _meaningful_tokens(source_text):
            return True
    return False


def assess_contextual_response(
    query: str,
    response: QalbuResponse,
    documents: list[QuranDocument],
    *,
    max_tokens: int,
) -> QualityReport:
    """Reject generic, uncited, quoted, or overconfident Indonesian answers."""
    query_text = query.casefold()
    answer = response.answer.casefold()
    issues: list[str] = []
    matched_group = next(
        (group for group in _CONTEXT_GROUPS if any(term in query_text for term in group)), ()
    )
    if matched_group and not any(term in answer for term in matched_group):
        issues.append("missing_context_ack")

    if not any(marker in answer for marker in _EMPATHY_MARKERS):
        issues.append("missing_empathy")
    if any(pattern in answer for pattern in _DISMISSIVE_PATTERNS):
        issues.append("dismissive_or_preachy")

    if documents:
        cited = {reference.parent_id for reference in response.references}
        if documents[0].id not in cited:
            issues.append("missing_primary_reference")

    cited_ids = {reference.parent_id for reference in response.references}
    cited_with_tafsir = any(doc.id in cited_ids and doc.tafsir for doc in documents)
    if cited_with_tafsir and "dalam tafsir yang tersedia" not in answer:
        issues.append("missing_tafsir_attribution")
    if documents and not any(bridge in answer for bridge in _GROUNDING_BRIDGES):
        issues.append("missing_grounding_bridge")
    if documents and not _has_source_anchor(answer, documents):
        issues.append("missing_source_anchor")

    if any(claim in answer for claim in _UNSUPPORTED_PROMISES):
        issues.append("unsupported_promise")
    if "remembrance" in answer:
        issues.append("mixed_language")
    if "ditepiskan" in answer:
        issues.append("unclear_wording")
    if re.search(r"[\u0600-\u06ff]", response.answer):
        issues.append("embedded_arabic_quote")
    if any(mark in response.answer for mark in ('"', "“", "”")) or re.search(
        r":\s*'", response.answer
    ):
        issues.append("embedded_quotation")
    if any(document.surah_name.casefold() in answer for document in documents):
        issues.append("embedded_source_identifier")
    if len(response.answer.split()) > max_tokens:
        issues.append("over_length")

    return QualityReport(passed=not issues, issues=tuple(issues))


def build_repair_query(
    original_prompt: str, response: QalbuResponse, report: QualityReport
) -> str:
    issues = ", ".join(report.issues)
    return (
        f"{original_prompt}\n\n"
        "DRAF SEBELUMNYA GAGAL QUALITY GATE:\n"
        f"{response.answer}\n"
        f"MASALAH: {issues}.\n"
        "Tulis ulang dari nol dalam Bahasa Indonesia. Akui emosi pengguna, hubungkan hanya "
        "SOURCE 1, mulai kalimat tafsir dengan tepat 'Dalam tafsir yang tersedia,' jika tafsir "
        "ada, sertakan satu gagasan yang jelas didukung Translation/Tafsir/Themes SOURCE 1, "
        "jangan bertanya atau menjanjikan hasil, jangan menulis aksara Arab, nama surah, nomor "
        "ayat, kutipan, atau kata Inggris dalam answer, hindari kalimat menggurui, dan cantumkan "
        "PARENT_ID SOURCE 1."
    )
