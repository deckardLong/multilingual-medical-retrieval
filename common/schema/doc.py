# Define doc schema

from pydantic import BaseModel, ConfigDict

# Schema
class Doc(BaseModel):
    model_config = ConfigDict(extra="ignore")
    uid: str                    
    doc_id: str                
    lang: str
    url: str
    title: str
    text: str                   
    schema_version: str | None = None
    source: str | None = None
    domain: str | None = None
    fetched_at: str | None = None
    content_hash: str | None = None