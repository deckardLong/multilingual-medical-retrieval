from common.schema import Candidate


def rrf_merge(lists: list[list[Candidate]], rrf_k: int, top_n: int) -> list[Candidate]:
    """Gộp kết quả của nhiều truy vấn con bằng RRF: điểm = tổng 1/(rrf_k + hạng). Hòa điểm giữ thứ tự xuất hiện đầu tiên."""
    score: dict[str, float] = {}
    first: dict[str, Candidate] = {}
    order: dict[str, int] = {}
    for lst in lists:
        for rank, c in enumerate(lst, start=1):
            score[c.chunk_id] = score.get(c.chunk_id, 0.0) + 1.0 / (rrf_k + rank)
            if c.chunk_id not in first:
                first[c.chunk_id] = c; order[c.chunk_id] = len(order)
    ids = sorted(score, key=lambda i: (-score[i], order[i]))[:top_n]
    return [first[i].model_copy(update={"score": score[i]}) for i in ids]