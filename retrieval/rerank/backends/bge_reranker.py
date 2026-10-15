import numpy as np
from retrieval.embedding.batching import with_oom_backoff

def _free_cuda(_new_batch: int) -> None:
    try:
        import torch
        torch.cuda.empty_cache()
    except Exception:
        pass

class BgeRerankerScorer:
    """bge-reranker-v2-m3 (cross-encoder) qua FlagEmbedding. normalize=True → sigmoid, điểm trong [0, 1].
    Hết VRAM thì tự giảm batch."""

    def __init__(self, cfg):
        from FlagEmbedding import FlagReranker
        self.cfg, self.batch_size = cfg, cfg.batch_size
        self.m = FlagReranker(cfg.model, use_fp16=cfg.fp16)

    def score_pairs(self, pairs: list[tuple[str, str]]) -> list[float]:
        if not pairs:
            return []
        data = [[q, p] for q, p in pairs]

        def run(bs: int):
            return self.m.compute_score(data, batch_size=bs, max_length=self.cfg.max_length, normalize=True)

        out, self.batch_size = with_oom_backoff(run, self.batch_size, on_oom=_free_cuda)
        return np.atleast_1d(np.asarray(out, dtype=np.float64)).tolist()