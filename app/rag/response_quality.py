import re
from dataclasses import dataclass

from app.models.chat import QalbuResponse, QuranReference
from app.models.quran import QuranDocument
from app.quran.curated_summaries import SAFE_REFLECTIONS_ID, TAFSIR_UNSUPPORTED_MARKERS


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
    """Check contextual grounding without rewriting model prose."""
    query_text = query.casefold()
    answer = response.answer.casefold()
    issues: list[str] = []

    matched_group = next(
        (group for group in _CONTEXT_GROUPS if any(term in query_text for term in group)),
        (),
    )
    if matched_group and not any(term in answer for term in matched_group):
        issues.append("missing_context_ack")

    if documents:
        cited = {reference.parent_id for reference in response.references}
        if documents[0].id not in cited:
            issues.append("missing_primary_reference")

    cited_ids = {reference.parent_id for reference in response.references}
    cited_with_tafsir = any(doc.id in cited_ids and doc.tafsir for doc in documents)
    if cited_with_tafsir and "tafsir" not in answer:
        issues.append("missing_tafsir_attribution")

    for document in documents:
        if document.id not in cited_ids:
            continue
        unsupported = TAFSIR_UNSUPPORTED_MARKERS.get(document.id, ())
        if unsupported and any(marker in answer for marker in unsupported):
            issues.append("unsupported_tafsir_detail")

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


def build_curated_safe_response(
    query: str, documents: list[QuranDocument]
) -> QalbuResponse | None:
    """Last-resort reviewed copy for an exact curated intent and source."""
    normalized = query.casefold()
    if not any(term in normalized for term in _CONTEXT_GROUPS[0]):
        return None
    source = next(
        (document for document in documents if document.id in SAFE_REFLECTIONS_ID),
        None,
    )
    if source is None:
        return None
    return QalbuResponse(
        answer=SAFE_REFLECTIONS_ID[source.id],
        references=[QuranReference(parent_id=source.id)],
    )


def build_repair_query(
    original_prompt: str, response: QalbuResponse, report: QualityReport
) -> str:
    issues = ", ".join(report.issues)
    return (
        f"{original_prompt}\n\n"
        "DRAF SEBELUMNYA GAGAL QUALITY GATE:\n"
        f"{response.answer}\n"
        f"MASALAH: {issues}.\n"
        "Tulis ulang dari nol. Tanggapi emosi yang benar-benar disebut pengguna. "
        "Hubungkan hanya SOURCE 1 dengan kondisi itu. Jika tafsir tersedia, kalimat "
        "terakhir wajib dimulai persis 'Dalam tafsir yang tersedia,'. Jangan bertanya, "
        "jangan memberi janji hasil, jangan memakai kata Inggris, dan cantumkan "
        "PARENT_ID SOURCE 1 pada references. Jangan tulis aksara Arab, nama surah, "
        "nomor ayat, atau kutipan Al-Qur'an di answer karena UI menampilkannya terpisah."
    )
