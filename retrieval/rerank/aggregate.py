# Aggregate

def max_over_queries(scores: list[float], n_queries: int, n_cands: int) -> list[float]:
    """scores xếp theo (truy vấn, chunk) → điểm mỗi chunk = điểm cao nhất qua các truy vấn con."""
    if len(scores) != n_queries * n_cands:
        raise ValueError(f"cần {n_queries * n_cands} điểm, nhận {len(scores)}")
    return [max(scores[qi * n_cands + ci] for qi in range(n_queries)) for ci in range(n_cands)]