from common.schema import Candidate


def _overlap_ratio(a: Candidate, b: Candidate) -> float:
    inter = min(a.end, b.end) - max(a.start, b.start)
    return max(0, inter) / max(1, min(a.end - a.start, b.end - b.start))


def pick_chunks(chunks: list[Candidate], k: int, max_overlap: float = 0.5) -> list[Candidate]:
    """Tối đa k chunk điểm cao nhất của một doc, bỏ chunk trùng quá `max_overlap` với chunk đã chọn."""
    out: list[Candidate] = []
    for c in sorted(chunks, key=lambda c: -c.score):
        if len(out) >= k:
            break
        if all(_overlap_ratio(c, o) <= max_overlap for o in out):
            out.append(c)
    return out