"""Deterministic theme hints for emotionally phrased Indonesian queries."""

import re

from pydantic import BaseModel, Field

from app.quran.themes import THEMES

_NON_REFLECTION_TOPICS = (
    "bitcoin",
    "kripto",
    "crypto",
    "saham",
    "forex",
    "harga emas",
    "cuaca",
    "skor pertandingan",
    "kode python",
    "javascript",
)


class QueryUnderstanding(BaseModel):
    normalized_query: str
    possible_themes: list[str] = Field(default_factory=list)
    possible_emotions: list[str] = Field(default_factory=list)
    retrieval_hints: list[str] = Field(default_factory=list)


def understand_query(query: str) -> QueryUnderstanding:
    normalized = re.sub(r"\s+", " ", query.strip().casefold())
    themes = [
        theme
        for theme, definition in THEMES.items()
        if any(keyword in normalized for keyword in definition["keywords"])
    ]
    hints = list(
        dict.fromkeys(
            term
            for theme in themes
            for term in THEMES[theme].get("retrieval_terms", [])
        )
    )
    return QueryUnderstanding(
        normalized_query=normalized,
        possible_themes=themes,
        possible_emotions=themes,
        retrieval_hints=hints,
    )


def enrich_query(query: str) -> tuple[str, list[str]]:
    understanding = understand_query(query)
    if not understanding.possible_themes:
        return query.strip(), []
    return (
        f"{understanding.normalized_query}\n"
        f"Tema refleksi: {', '.join(understanding.possible_themes)}\n"
        f"Konsep terkait: {', '.join(understanding.retrieval_hints)}",
        understanding.possible_themes,
    )


def is_out_of_scope(query: str) -> bool:
    """Reject obvious factual/tool queries unless the user also expresses distress."""
    understanding = understand_query(query)
    return not understanding.possible_themes and any(
        topic in understanding.normalized_query for topic in _NON_REFLECTION_TOPICS
    )
