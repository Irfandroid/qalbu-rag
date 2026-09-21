from app.models.quran import QuranDocument
from app.quran.curated_summaries import TAFSIR_SUMMARIES_ID


def build_context(documents: list[QuranDocument]) -> str:
    sections: list[str] = []
    for index, doc in enumerate(documents, start=1):
        tafsir_summary = TAFSIR_SUMMARIES_ID.get(doc.id)
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
                        f"{doc.translation or '[not provided]'}"
                    ),
                    (
                        "Tafsir: [original Arabic is rendered separately by the UI]"
                        if tafsir_summary
                        else f"Tafsir: {doc.tafsir or '[not provided]'}"
                    ),
                    (
                        "Reviewed Indonesian tafsir summary (working paraphrase, "
                        "not an official translation): "
                        f"{tafsir_summary or '[not provided]'}"
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
                        else str(doc.source)
                    ),
                ]
            )
        )
    return "<retrieved_context>\n" + "\n\n".join(sections) + "\n</retrieved_context>"
