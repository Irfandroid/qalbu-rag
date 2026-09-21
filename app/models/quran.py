from typing import Any

from pydantic import BaseModel, Field, model_validator


class QuranDocument(BaseModel):
    id: str
    surah_number: int = Field(ge=1, le=114)
    surah_name: str = Field(min_length=1)
    ayah_start: int = Field(ge=1)
    ayah_end: int = Field(ge=1)
    arabic_text: str | None = None
    translation: str | None = None
    tafsir: str | None = None
    themes: list[str] = Field(default_factory=list)
    source: dict[str, str]
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def valid_ayah_range(self) -> "QuranDocument":
        if self.ayah_end < self.ayah_start:
            raise ValueError("ayah_end must not be before ayah_start")
        if not self.source.get("quran"):
            raise ValueError("source.quran is required")
        return self


class QuranChunk(BaseModel):
    id: str
    parent_id: str
    chunk_type: str
    content: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)
