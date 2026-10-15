import math

class RerankError(RuntimeError):
    pass

def validate_scores(scores: list[float], n: int) -> None:
    """Chốt chặn: đủ số điểm, hữu hạn, nằm trong [0, 1]."""
    if len(scores) != n:
        raise RerankError(f"nhận {len(scores)} điểm, cần {n}")
    for i, s in enumerate(scores):
        if not math.isfinite(s) or not (0.0 <= s <= 1.0):
            raise RerankError(f"điểm thứ {i} không hợp lệ: {s}")