import math
import numpy as np
from .types import Encoded

class EmbeddingError(RuntimeError):
    pass

def validate_encoded(enc: Encoded, n: int, dim: int, *, use_sparse: bool, norm_tol: float = 0.02) -> None:
    """Chốt chặn trước khi ghi: hình dạng đúng, không NaN/Inf, dense đã chuẩn hóa, sparse hợp lệ."""
    d = enc.dense
    if d.shape != (n, dim):
        raise EmbeddingError(f"dense có hình {d.shape}, cần {(n, dim)}")
    if not np.isfinite(d).all():
        raise EmbeddingError("dense chứa NaN/Inf (thường do fp16 tràn số)")
    if n:
        norms = np.linalg.norm(d.astype(np.float32), axis=1)
        if np.abs(norms - 1.0).max() > norm_tol:
            raise EmbeddingError(f"dense chưa chuẩn hóa L2: chuẩn lệch tối đa {np.abs(norms - 1).max():.3f}")
    if len(enc.sparse) != n:
        raise EmbeddingError(f"sparse có {len(enc.sparse)} phần tử, cần {n}")
    for i, sv in enumerate(enc.sparse):
        if len(sv.indices) != len(sv.values):
            raise EmbeddingError(f"sparse[{i}]: indices và values lệch độ dài")
        if len(set(sv.indices)) != len(sv.indices) or any(k < 0 for k in sv.indices):
            raise EmbeddingError(f"sparse[{i}]: indices trùng hoặc âm")
        if any((not math.isfinite(v)) or v <= 0 for v in sv.values):
            raise EmbeddingError(f"sparse[{i}]: values phải hữu hạn và > 0")
    if use_sparse and n >= 5 and all(not sv.indices for sv in enc.sparse):
        raise EmbeddingError("use_sparse = true nhưng toàn bộ sparse rỗng")