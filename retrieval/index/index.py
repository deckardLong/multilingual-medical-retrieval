from common.schema import Chunk
from pydantic import model_validator

# đủ để dựng Candidate (C2) và để reranker có ctx
REQUIRED_PAYLOAD = {"chunk_id", "uid", "doc_id", "start", "end", "p_start", "p_end", "ctx", "text"}

@model_validator(mode="after")
def _check(self):
    miss = REQUIRED_PAYLOAD - set(self.payload_fields)
    if miss:
        raise ValueError(f"index.payload_fields thiếu: {sorted(miss)}")
    unknown = set(self.payload_fields) - set(Chunk.model_fields)
    if unknown:
        raise ValueError(f"index.payload_fields không có trong Chunk: {sorted(unknown)}")
    if not {"uid"} <= set(self.payload_indexes):
        raise ValueError("index.payload_indexes phải có 'uid' (cần để xóa theo doc)")
    if self.upsert_batch <= 0:
        raise ValueError("index.upsert_batch phải > 0")
    return self