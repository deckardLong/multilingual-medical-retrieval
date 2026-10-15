# Build pair scorer
def build_pair_scorer(cfg):
    """Tạo bộ chấm điểm theo cfg.backend. Import trễ để máy không có GPU vẫn chạy được test."""
    if cfg.backend == "fake":
        from .backends.fake import FakePairScorer
        return FakePairScorer(cfg)
    if cfg.backend == "bge_reranker":
        from .backends.bge_reranker import BgeRerankerScorer
        return BgeRerankerScorer(cfg)
    raise ValueError(f"backend không hỗ trợ: {cfg.backend}")