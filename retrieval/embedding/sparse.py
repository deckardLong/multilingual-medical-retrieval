# Lexical weight (BM25)

import math
from common.schema import  SparseVec

EMPTY = SparseVec([], [])

# To sparse
def to_sparse(weights: dict) -> SparseVec:
    items = sorted((int(k), float(v)) for k, v in weights.items() if math.isfinite(float(v)) and float(v) > 0)  # remove weights <= 0 or infinite
    return SparseVec([k for k, _ in items], [v for _, v in items])