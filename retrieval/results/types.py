from pydantic import BaseModel
from common.schema import Candidate


class QueryResult(BaseModel):
    qid: int
    query: str
    candidates: list[Candidate]


class Query(BaseModel):
    qid: int
    text: str