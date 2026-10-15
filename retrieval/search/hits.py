from common.schema import Candidate

_FIELDS = ("chunk_id", "uid", "doc_id", "start", "end", "p_start", "p_end", "text", "ctx")


def hit_to_candidate(hit) -> Candidate:
    """Điểm Qdrant (đã kèm payload) → Candidate; score = điểm RRF của Qdrant ở giai đoạn này."""
    p = hit.payload
    return Candidate(score=float(hit.score), **{k: p[k] for k in _FIELDS if k in p})