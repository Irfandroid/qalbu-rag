"""Deterministic theme hints for emotionally phrased Indonesian queries."""

import re
from enum import StrEnum

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
_REAL_TIME_TERMS = (
    "hari ini",
    "sekarang",
    "terbaru",
    "terkini",
    "real time",
    "real-time",
    "besok",
    "live",
)
_EMOTIONAL_TERMS = (
    "cemas",
    "sedih",
    "hampa",
    "marah",
    "takut",
    "tertinggal",
    "kehampaan",
    "kehilangan arah",
    "capek hidup",
    "menderita",
    "yatim",
    "kdrt",
)


class Intent(StrEnum):
    EMOTIONAL_REFLECTION = "emotional_reflection"
    QURANIC_INFORMATION = "quranic_information"
    ISLAMIC_GUIDANCE = "islamic_guidance"
    PRACTICAL_LIFE_GUIDANCE = "practical_life_guidance"
    GENERAL_INFORMATION = "general_information"
    OUT_OF_SCOPE = "out_of_scope"


_INTENT_TERMS: dict[Intent, tuple[str, ...]] = {
    Intent.QURANIC_INFORMATION: (
        "ayat",
        "surah",
        "surat",
        "terjemahan al quran",
        "tafsir",
        "konteks ayat",
        "juz",
        "mushaf",
        "quran",
        "qur'an",
        "al-quran",
        "al-qur'an",
        "al quran",
        "alquran",
    ),
    Intent.ISLAMIC_GUIDANCE: (
        "dalam islam",
        "menurut islam",
        "halal",
        "haram",
        "wajib",
        "ibadah",
        "shalat",
        "salat",
        "puasa",
        "zakat",
        "nikah",
        "pernikahan",
        "muamalah",
        "hadis",
        "hadits",
        "fatwa",
        "ustaz",
        "ustadz",
    ),
    Intent.PRACTICAL_LIFE_GUIDANCE: (
        "kerja",
        "pekerjaan",
        "karier",
        "kuliah",
        "sekolah",
        "belajar",
        "uang",
        "keuangan",
        "anggaran",
        "utang",
        "bulanan",
        "menabung",
        "produktif",
        "keputusan",
        "rencana hidup",
    ),
    Intent.GENERAL_INFORMATION: (
        "python",
        "javascript",
        "program",
        "pemrograman",
        "coding",
        "kode",
        "ai",
        "llm",
        "teknologi",
        "sains",
        "matematika",
        "fisika",
        "apa itu",
        "bagaimana cara",
    ),
    Intent.OUT_OF_SCOPE: (
        "bitcoin",
        "kripto",
        "crypto",
        "saham",
        "forex",
        "harga",
        "cuaca",
        "skor pertandingan",
        "berita terbaru",
        "cek akun",
        "pesankan",
        "kirimkan",
    ),
}


class QueryUnderstanding(BaseModel):
    normalized_query: str
    possible_themes: list[str] = Field(default_factory=list)
    possible_emotions: list[str] = Field(default_factory=list)
    retrieval_hints: list[str] = Field(default_factory=list)


class IntentDecision(BaseModel):
    primary_intent: Intent
    secondary_intents: list[Intent] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    requires_quran: bool
    needs_clarification: bool = False


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


def classify_intent(query: str) -> IntentDecision:
    """Classify routing needs locally without diagnosing or calling a provider."""
    understanding = understand_query(query)
    normalized = understanding.normalized_query
    scores = {intent: 0 for intent in Intent}

    if understanding.possible_themes:
        scores[Intent.EMOTIONAL_REFLECTION] += 2
    if any(term in normalized for term in _EMOTIONAL_TERMS):
        scores[Intent.EMOTIONAL_REFLECTION] += 3
    for intent, terms in _INTENT_TERMS.items():
        weight = 4 if intent in {
            Intent.QURANIC_INFORMATION,
            Intent.ISLAMIC_GUIDANCE,
        } else 2
        scores[intent] += weight * sum(1 for term in terms if term in normalized)
    if any(term in normalized for term in _REAL_TIME_TERMS):
        scores[Intent.OUT_OF_SCOPE] += 3

    precedence = (
        Intent.EMOTIONAL_REFLECTION,
        Intent.QURANIC_INFORMATION,
        Intent.ISLAMIC_GUIDANCE,
        Intent.PRACTICAL_LIFE_GUIDANCE,
        Intent.GENERAL_INFORMATION,
        Intent.OUT_OF_SCOPE,
    )
    ranked = sorted(scores, key=lambda intent: (-scores[intent], precedence.index(intent)))
    top = ranked[0]
    top_score = scores[top]
    if top_score == 0:
        return IntentDecision(
            primary_intent=Intent.GENERAL_INFORMATION,
            confidence=0,
            requires_quran=False,
            needs_clarification=True,
        )
    nonzero = [intent for intent in ranked if scores[intent] > 0]
    total = sum(scores.values())
    secondary = [intent for intent in nonzero[1:3] if intent != top]
    confidence = min(1.0, top_score / max(total, 1))
    needs_clarification = len(nonzero) > 1 and top_score == scores[nonzero[1]]
    return IntentDecision(
        primary_intent=top,
        secondary_intents=secondary,
        confidence=confidence,
        requires_quran=top
        in {
            Intent.EMOTIONAL_REFLECTION,
            Intent.QURANIC_INFORMATION,
            Intent.ISLAMIC_GUIDANCE,
        },
        needs_clarification=needs_clarification,
    )


def is_out_of_scope(query: str) -> bool:
    """Reject obvious factual/tool queries unless the user also expresses distress."""
    understanding = understand_query(query)
    if understanding.possible_themes:
        return False
    return classify_intent(query).primary_intent == Intent.OUT_OF_SCOPE or any(
        topic in understanding.normalized_query for topic in _NON_REFLECTION_TOPICS
    )
