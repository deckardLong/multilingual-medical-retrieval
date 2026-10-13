# Define chunk schema

from pydantic import BaseModel

# Schema
class Chunk(BaseModel):
    chunk_id: str       # # f"{uid}#{n}"      
    uid: str
    doc_id: str
    lang: str
    start: int                 
    end: int
    p_start: int               
    p_end: int
    heading: str
    ctx: str                  
    text: str
    n_tokens: int
    chunker_ver: str          