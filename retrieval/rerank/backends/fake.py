import re

_WORD = re.compile(r"\w+", re.UNICODE)


class FakePairScorer:
    """Điểm = tỷ lệ từ của truy vấn xuất hiện trong passage (0–1)."""

    def __init__(self, cfg):
        self.cfg = cfg

    def score_pairs(self, pairs: list[tuple[str, str]]) -> list[float]:
        out = []
        for q, p in pairs:
            qs = set(_WORD.findall(q.lower()))
            ps = set(_WORD.findall(p.lower()))
            out.append(len(qs & ps) / len(qs) if qs else 0.0)
        return out