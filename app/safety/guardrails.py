import re
import unicodedata
from dataclasses import dataclass
from enum import StrEnum


class SafetyLevel(StrEnum):
    NORMAL = "normal"
    DISTRESS = "distress"
    HIGH_DISTRESS = "high_distress"
    IMMEDIATE_DANGER = "immediate_danger"


@dataclass(frozen=True)
class SafetyDecision:
    level: SafetyLevel
    response: str | None = None
    category: str | None = None
    pattern_id: str | None = None


class SafetyGuardrails:
    """Deterministic, network-free safety gate that always runs before RAG."""

    _slang = {
        "pgn": "ingin",
        "pngn": "ingin",
        "mau bundir": "ingin bunuh diri",
        "bundir": "bunuh diri",
        "selfharm": "self harm",
        "ga sanggup": "tidak sanggup",
        "gak sanggup": "tidak sanggup",
        "nggak sanggup": "tidak sanggup",
    }
    _immediate_patterns = (
        ("suicide_id", re.compile(r"\b(bunuh diri|mengakhiri hidup|ingin mati|pengen mati)\b")),
        ("self_harm_id", re.compile(r"\b(menyakiti|melukai) diri(?: sendiri)?\b")),
        ("harm_other_id", re.compile(r"\b(melukai|membunuh) orang\b")),
        ("suicide_en", re.compile(r"\b(kill myself|end my life|want to die|suicide)\b")),
        ("self_harm_en", re.compile(r"\b(self harm|hurt myself)\b")),
    )
    _hard_negative_patterns = (
        re.compile(r"\b(tidak|nggak|gak|bukan) (ingin |mau )?(bunuh diri|mati|menyakiti diri)\b"),
        re.compile(r"\b(berita|film|buku|artikel|penelitian)\b.*\b(bunuh diri|suicide)\b"),
    )
    high_distress_terms = ("putus asa", "tidak sanggup", "self harm")
    distress_terms = ("sedih", "cemas", "berat", "stres", "kehilangan harapan")

    @classmethod
    def normalize(cls, message: str) -> str:
        value = unicodedata.normalize("NFKD", message.casefold())
        value = "".join(char for char in value if not unicodedata.combining(char))
        value = value.translate(
            {
                ord("0"): "o",
                ord("1"): "i",
                ord("3"): "e",
                ord("4"): "a",
                ord("5"): "s",
            }
        )
        value = re.sub(r"(.)\1{2,}", r"\1", value)
        value = re.sub(r"[^a-z\s]", " ", value)
        value = re.sub(r"\s+", " ", value).strip()
        for slang, canonical in cls._slang.items():
            value = re.sub(rf"\b{re.escape(slang)}\b", canonical, value)
        return value

    def check(self, message: str) -> SafetyDecision:
        normalized = self.normalize(message)
        if any(pattern.search(normalized) for pattern in self._hard_negative_patterns):
            return SafetyDecision(SafetyLevel.NORMAL)
        for pattern_id, pattern in self._immediate_patterns:
            if pattern.search(normalized):
                return SafetyDecision(
                    SafetyLevel.IMMEDIATE_DANGER,
                    (
                        "Aku turut prihatin kamu sedang menghadapi ini. Jika ada risiko "
                        "menyakiti diri sendiri atau orang lain sekarang, hubungi layanan "
                        "darurat setempat atau orang tepercaya yang bisa menemani kamu. "
                        "Qalbu bukan pengganti bantuan krisis atau profesional."
                    ),
                    category="immediate_danger",
                    pattern_id=pattern_id,
                )
        if any(term in normalized for term in self.high_distress_terms):
            return SafetyDecision(SafetyLevel.HIGH_DISTRESS, category="high_distress")
        if any(term in normalized for term in self.distress_terms):
            return SafetyDecision(SafetyLevel.DISTRESS, category="distress")
        return SafetyDecision(SafetyLevel.NORMAL)
