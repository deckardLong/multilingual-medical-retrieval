from .registry import build_pair_scorer
from .service import Reranker, NoopReranker


def build_reranker(cfg):
    """Điểm vào duy nhất: cfg.enabled=false thì không tải model."""
    return Reranker(build_pair_scorer(cfg), cfg) if cfg.enabled else NoopReranker()