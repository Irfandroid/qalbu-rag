from typing import Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500)
    lang: Literal["id", "en"] = "id"
    tone: Literal["lembut", "netral", "singkat"] = "lembut"
    max_tokens: int = Field(default=72, ge=40, le=120)
    history: list[ChatMessage] = Field(default_factory=list, max_length=3)
    show_sources: bool = False


class QuranReference(BaseModel):
    parent_id: str
    # Local models sometimes return only parent_id. CitationValidator fills the
    # canonical fields from an actually retrieved parent before a reference can
    # reach an API response.
    surah_number: int | None = None
    surah_name: str | None = None
    ayah_start: int | None = None
    ayah_end: int | None = None


class QuranEvidence(QuranReference):
    arabic_text: str | None = None
    translation: str | None = None
    translation_language: str | None = None
    translation_name: str | None = None
    tafsir: str | None = None
    source_status: str
    themes: list[str] = Field(default_factory=list)
    score: float | None = None


class QalbuDraft(BaseModel):
    answer: str
    references: list[QuranReference]
    safety_note: str | None = None


class QalbuResponse(QalbuDraft):
    evidence: list[QuranEvidence] = Field(default_factory=list)


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail
