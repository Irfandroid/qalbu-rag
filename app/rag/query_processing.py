"""Deterministic theme hints for emotionally phrased Indonesian queries."""

from app.quran.themes import THEMES


def enrich_query(query: str) -> tuple[str, list[str]]:
    normalized = query.casefold()
    matched = [
        theme
        for theme, definition in THEMES.items()
        if any(keyword in normalized for keyword in definition["keywords"])
    ]
    if not matched:
        return query, []
    return f"{query}\nTema refleksi: {', '.join(matched)}", matched
