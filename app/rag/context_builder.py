from app.models.quran import QuranDocument


def _bounded(value: str | None, max_words: int) -> str:
    if not value:
        return "[not provided]"
    words = value.split()
    if len(words) <= max_words:
        return value
    return " ".join(words[:max_words]) + " [truncated by context builder]"


def build_context(documents: list[QuranDocument], max_context_tokens: int = 1800) -> str:
    sections: list[str] = []
    words_per_parent = max(120, max_context_tokens // max(len(documents), 1) // 2)
    for index, doc in enumerate(documents, start=1):
        sections.append(
            "\n".join(
                [
                    f"SOURCE {index}",
                    f"PARENT_ID: {doc.id}",
                    f"Surah: {doc.surah_name} ({doc.surah_number})",
                    f"Ayah: {doc.ayah_start}-{doc.ayah_end}",
                    "Arabic: [rendered separately by the UI; do not quote or reproduce]",
                    (
                        "Translation "
                        f"({doc.metadata.get('translation_language', 'unknown')}, "
                        f"{doc.metadata.get('translation_name', 'unnamed')}): "
                        f"{_bounded(doc.translation, words_per_parent // 3)}"
                    ),
                    (
                        f"Tafsir ({doc.metadata.get('tafsir_language', 'unknown')}, "
                        f"{doc.metadata.get('tafsir_name', 'unnamed')}): "
                        f"{_bounded(doc.tafsir, words_per_parent)}"
                    ),
                    f"Themes: {', '.join(doc.themes) or '[not provided]'}",
                    "Source status: "
                    + (
                        "TEMPORARY metadata, not scripture"
                        if doc.metadata.get("temporary")
                        else (
                            "COMMUNITY DATASET: not official Kemenag source; "
                            "cite provenance clearly"
                        )
                        if doc.metadata.get("unverified_community_source")
                        else (
                            "USER-SUPPLIED INDONESIAN SNAPSHOT: provenance unverified; "
                            "do not call it official Kemenag"
                            if doc.metadata.get("source_provider")
                            == "user_indonesian_snapshot"
                            else str(doc.source)
                        )
                    ),
                ]
            )
        )
    return "<retrieved_context>\n" + "\n\n".join(sections) + "\n</retrieved_context>"
