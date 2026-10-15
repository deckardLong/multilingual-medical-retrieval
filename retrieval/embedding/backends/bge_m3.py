import numpy as np
from typing import cast
from common.schema import SparseVec
from ..batching import with_oom_backoff
from ..sparse import to_sparse
from ..types import Encoded

def _free_cuda(_new_batch: int) -> None:
    try:
        import torch
        torch.cuda.empty_cache()
    except Exception:
        pass

class BgeM3Embedder:
    """BGE-M3 qua FlagEmbedding (dense 1024 chiều + sparse). GPU chọn bằng CUDA_VISIBLE_DEVICES.
    BGE-M3 không cần tiền tố chỉ dẫn cho truy vấn; chỉ khác độ dài tối đa."""

    def __init__(self, cfg):
        from FlagEmbedding import BGEM3FlagModel
        self.cfg, self.dim, self.batch_size = cfg, cfg.dim, cfg.batch_size
        self.m = BGEM3FlagModel(cfg.model, use_fp16=cfg.fp16)

    def _encode(self, texts: list[str], max_length: int) -> Encoded:
        if not texts:
            return Encoded(np.zeros((0, self.dim), np.float32), [])

        def run(bs: int):
            return self.m.encode(texts, batch_size=bs, max_length=max_length, return_dense=True,
                                 return_sparse=self.cfg.use_sparse, return_colbert_vecs=False)

        out, self.batch_size = with_oom_backoff(run, self.batch_size, on_oom=_free_cuda)
        dense = np.asarray(out["dense_vecs"], dtype=np.float32)
        if self.cfg.use_sparse:
            sparse = [to_sparse(cast(dict[str, float], w)) for w in out["lexical_weights"]]
        else:
            sparse = [SparseVec([], []) for _ in texts]
        return Encoded(dense=dense, sparse=sparse)

    def encode_docs(self, texts: list[str]) -> Encoded:
        return self._encode(texts, self.cfg.max_length)

    def encode_queries(self, texts: list[str]) -> Encoded:
        return self._encode(texts, self.cfg.query_max_length)