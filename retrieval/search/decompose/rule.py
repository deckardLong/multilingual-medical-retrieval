from .splitters import count_units, split_conjunction, split_questions
from .types import Decomposed

def _norm(s: str) -> str:
    return " ".join(s.lower().split())

class RuleDecomposer:
    """Tách truy vấn đa ý thành các truy vấn con bằng luật (không cần LLM, xác định, nhanh)."""

    def __init__(self, cfg):
        self.cfg = cfg

    def decompose(self, query: str) -> Decomposed:
        parts: list[str] = []
        for sent in split_questions(query):
            parts += split_conjunction(sent, self.cfg.min_part_tokens)
        seen, subs = {_norm(query)}, []
        for p in parts:
            if count_units(p) >= 2 and _norm(p) not in seen:
                seen.add(_norm(p)); subs.append(p)
        if len(parts) < 2:                              # không có gì để tách
            subs = []
        subs = subs[: self.cfg.max_subqueries]
        if not subs:
            return Decomposed(query, [query], [])
        return Decomposed(query, ([query] if self.cfg.keep_original else []) + subs, subs)