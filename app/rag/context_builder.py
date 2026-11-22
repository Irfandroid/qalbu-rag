"""Build the bounded, structured context block given to the LLM."""

from app.models.quran import QuranDocument

TRUNCATION_MARKER = " [truncated by context builder]"
NOT_PROVIDED = "[not provided]"
MIN_WORDS_PER_PARENT = 120


def build_context(documents: list[QuranDocument], max_context_tokens: int = 1800) -> str:
    words_per_parent = max(
        MIN_WORDS_PER_PARENT,
        max_context_tokens // max(len(documents), 1) // 2,
    )
    sections = [
        _source_section(index, document, words_per_parent)
        for index, document in enumerate(documents, start=1)
    ]
    return "<retrieved_context>\n" + "\n\n".join(sections) + "\n</retrieved_context>"


def _source_section(index: int, document: QuranDocument, words_per_parent: int) -> str:
    metadata = document.metadata
    return "\n".join(
        [
            f"SOURCE {index}",
            f"PARENT_ID: {document.id}",
            f"Surah: {document.surah_name} ({document.surah_number})",
            f"Ayah: {document.ayah_start}-{document.ayah_end}",
            "Arabic: [rendered separately by the UI; do not quote or reproduce]",
            (
                "Translation "
                f"({metadata.get('translation_language', 'unknown')}, "
                f"{metadata.get('translation_name', 'unnamed')}): "
                f"{_bounded(document.translation, words_per_parent // 3)}"
            ),
            (
                f"Tafsir ({metadata.get('tafsir_language', 'unknown')}, "
                f"{metadata.get('tafsir_name', 'unnamed')}): "
                f"{_bounded(document.tafsir, words_per_parent)}"
            ),
            f"Themes: {', '.join(document.themes) or NOT_PROVIDED}",
            f"Source status: {_source_status(document)}",
        ]
    )


def _bounded(value: str | None, max_words: int) -> str:
    if not value:
        return NOT_PROVIDED
    words = value.split()
    if len(words) <= max_words:
        return value
    return " ".join(words[:max_words]) + TRUNCATION_MARKER


def _source_status(document: QuranDocument) -> str:
    metadata = document.metadata
    if metadata.get("temporary"):
        return "TEMPORARY metadata, not scripture"
    if metadata.get("unverified_community_source"):
        return "COMMUNITY DATASET: not official Kemenag source; cite provenance clearly"
    if metadata.get("source_provider") == "user_indonesian_snapshot":
        return (
            "USER-SUPPLIED INDONESIAN SNAPSHOT: provenance unverified; "
            "do not call it official Kemenag"
        )
    return str(document.source)
