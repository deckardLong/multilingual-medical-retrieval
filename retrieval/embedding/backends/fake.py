import hashlib, math, re
import numpy as np
from common.schema import SparseVec
from ..types import Encoded

_WORD = re.compile(r"\w+", re.UNICODE)
VOCAB = 250_002

def _h(token: str) -> int:
    return int.from_bytes(hashlib.md5(token.encode()).digest()[:8], "big")

class FakeEmbedder:
    """Băm từ vào vector: văn bản có từ chung thì cosine cao hơn, đủ để test index/hybrid/rerank."""
    def __init__(self, cfg):
        self.cfg, self.dim = cfg, cfg.dim

    def _one(self, text: str, max_length: int):
        toks = _WORD.findall(text.lower())[:max_length]
        v = np.zeros(self.dim, np.float32); tf: dict[int, int] = {}
        for t in toks:
            h = _h(t); v[h % self.dim] += 1.0 if (h >> 40) & 1 else -1.0
            tf[h % VOCAB] = tf.get(h % VOCAB, 0) + 1
        n = float(np.linalg.norm(v))
        if n == 0:
            v[0], n = 1.0, 1.0
        top = max(tf.values(), default=1)
        items = sorted((k, math.log1p(c) / math.log1p(top)) for k, c in tf.items())
        return v / n, SparseVec([k for k, _ in items], [w for _, w in items])

    def _enc(self, texts: list[str], max_length: int) -> Encoded:
        rows = [self._one(t, max_length) for t in texts]
        dense = np.stack([r[0] for r in rows]) if rows else np.zeros((0, self.dim), np.float32)
        sparse = [r[1] for r in rows] if self.cfg.use_sparse else [SparseVec([], []) for _ in rows]
        return Encoded(dense, sparse)

    def encode_docs(self, texts):   
        return self._enc(texts, self.cfg.max_length)
    
    def encode_queries(self, texts): 
        return self._enc(texts, self.cfg.query_max_length)