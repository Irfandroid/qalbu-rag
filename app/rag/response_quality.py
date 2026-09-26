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

    if documents:
        cited = {reference.parent_id for reference in response.references}
        if documents[0].id not in cited:
            issues.append("missing_primary_reference")

    cited_ids = {reference.parent_id for reference in response.references}
    cited_with_tafsir = any(doc.id in cited_ids and doc.tafsir for doc in documents)
    if cited_with_tafsir and "dalam tafsir yang tersedia" not in answer:
        issues.append("missing_tafsir_attribution")

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
        "ada, jangan bertanya atau menjanjikan hasil, jangan menulis aksara Arab, nama surah, "
        "nomor ayat, kutipan, atau kata Inggris dalam answer, dan cantumkan PARENT_ID SOURCE 1."
    )
