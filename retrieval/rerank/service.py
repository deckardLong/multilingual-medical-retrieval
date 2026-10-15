from common.schema import Candidate
from .aggregate import max_over_queries
from .pairs import build_pairs
from .validate import validate_scores

class Reranker:
    """Chấm lại pool chunk bằng cross-encoder rồi sắp giảm dần theo điểm."""

    def __init__(self, scorer, cfg):
        self.scorer, self.cfg = scorer, cfg

    def rerank(self, queries: list[str], cands: list[Candidate]) -> list[Candidate]:
        """queries[0] là truy vấn gốc; các phần tử sau là truy vấn con (nếu có).
        Trả về bản sao Candidate với score = điểm rerank; danh sách đầu vào không bị sửa."""
        if not cands:
            return []
        if not queries:
            raise ValueError("cần ít nhất một truy vấn")
        qs = queries if self.cfg.query_mode == "max_over_subqueries" else queries[:1]
        raw = self.scorer.score_pairs(build_pairs(qs, cands))
        validate_scores(raw, len(qs) * len(cands))
        final = max_over_queries(raw, len(qs), len(cands))
        order = sorted(range(len(cands)), key=lambda i: (-final[i], i))     # hòa điểm giữ thứ tự cũ
        return [cands[i].model_copy(update={"score": final[i]}) for i in order]

class NoopReranker:
    """rerank.enabled=false: giữ nguyên điểm truy hồi, chỉ sắp giảm dần."""

    def rerank(self, queries: list[str], cands: list[Candidate]) -> list[Candidate]:
        return sorted(cands, key=lambda c: -c.score)