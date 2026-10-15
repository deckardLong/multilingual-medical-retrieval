import numpy as np
from ..batching import with_oom_backoff
from ..device import pick_device
from ..types import Encoded

def _free_cuda(_n: int) -> None:
    try:
        import torch
        torch.cuda.empty_cache()
    except Exception:
        pass

class StDenseEmbedder:
    """Mọi model chỉ-dense qua sentence-transformers. Truy vấn thường cần tiền tố chỉ dẫn (cfg.query_prompt)."""

    def __init__(self, cfg):
        from sentence_transformers import SentenceTransformer
        self.cfg, self.dim, self.batch_size = cfg, cfg.dim, cfg.batch_size
        model_kwargs = {"torch_dtype": "float16"} if cfg.fp16 else None
        self.m = SentenceTransformer(cfg.model, device=pick_device(), model_kwargs=model_kwargs)

    def _encode(self, texts: list[str], max_length: int, prompt: str) -> Encoded:
        if not texts:
            return Encoded(np.zeros((0, self.dim), np.float32), [])
        self.m.max_seq_length = max_length

        def run(bs: int):
            return self.m.encode(texts, prompt=prompt or None, batch_size=bs,
                                 normalize_embeddings=True, convert_to_numpy=True)

        out, self.batch_size = with_oom_backoff(run, self.batch_size, on_oom=_free_cuda)
        return Encoded(np.asarray(out, dtype=np.float32), [])

    def encode_docs(self, texts: list[str]) -> Encoded:
        return self._encode(texts, self.cfg.max_length, self.cfg.doc_prompt)

    def encode_queries(self, texts: list[str]) -> Encoded:
        return self._encode(texts, self.cfg.query_max_length, self.cfg.query_prompt)