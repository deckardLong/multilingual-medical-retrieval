from common.schema import Candidate
from retrieval.chunking.context import embed_text

def passage_of(c: Candidate) -> str:
    """Văn bản đưa vào reranker: tiền tố ngữ cảnh (nếu có) + nội dung chunk."""
    return embed_text(getattr(c, "ctx", "") or "", c.text or "")

def build_pairs(queries: list[str], cands: list[Candidate]) -> list[tuple[str, str]]:
    """Mọi cặp (query, chunk), xếp theo truy vấn trước: chỉ số cặp = qi * len(cands) + ci."""
    passages = [passage_of(c) for c in cands]
    return [(q, p) for q in queries for p in passages]