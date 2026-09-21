from pydantic import BaseModel


class RetrievalResult(BaseModel):
    child_id: str
    parent_id: str
    score: float
    chunk_type: str
    surah_number: int
    surah_name: str
    ayah_start: int
    ayah_end: int
