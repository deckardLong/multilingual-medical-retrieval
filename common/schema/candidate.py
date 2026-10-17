# Define candidate schema

from pydantic import BaseModel

# Schema
class Candidate(BaseModel):
    chunk_id: str
    uid: str
    doc_id: str
    start: int
    end: int
    p_start: int
    p_end: int
    score: float
    text: str | None = None
    ctx: str | None = None