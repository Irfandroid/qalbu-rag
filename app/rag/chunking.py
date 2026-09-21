from app.models.quran import QuranChunk, QuranDocument

CHILD_WORDS = 120
CHILD_OVERLAP_WORDS = 20


def split_words(content: str) -> list[str]:
    words = content.split()
    if len(words) <= CHILD_WORDS:
        return [content.strip()]
    chunks: list[str] = []
    step = CHILD_WORDS - CHILD_OVERLAP_WORDS
    for start in range(0, len(words), step):
        part = words[start : start + CHILD_WORDS]
        if not part:
            break
        chunks.append(" ".join(part))
        if start + CHILD_WORDS >= len(words):
            break
    return chunks


def make_chunks(document: QuranDocument) -> list[QuranChunk]:
    candidates = {
        "translation": document.translation,
        "tafsir": document.tafsir,
        "themes": "; ".join(document.themes) if document.themes else None,
    }
    chunks: list[QuranChunk] = []
    for chunk_type, content in candidates.items():
        if not content or not content.strip():
            continue
        parts = split_words(content)
        for index, part in enumerate(parts):
            chunks.append(
                QuranChunk(
                    id=f"{document.id}:{chunk_type}:{index:03d}",
                    parent_id=document.id,
                    chunk_type=chunk_type,
                    content=part,
                    metadata={
                        "part_index": index,
                        "part_count": len(parts),
                        "source_temporary": document.metadata.get("temporary", False),
                        "source_provider": document.metadata.get("source_provider", "temporary"),
                        "translation_language": document.metadata.get("translation_language"),
                        "unverified_community_source": (
                            document.metadata.get("unverified_community_source", False)
                            or (
                                chunk_type == "tafsir"
                                and document.metadata.get(
                                    "tafsir_unverified_community_source", False
                                )
                            )
                        ),
                    },
                )
            )
    return chunks
