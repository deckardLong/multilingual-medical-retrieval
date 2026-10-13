# Assign parent pieces

from .types import Piece

def assign_parents(pieces: list[Piece], max_tokens: int) -> list[tuple[int, int]]:
    """Parent span for each piece"""
    n, i = len(pieces), 0
    out: list[tuple[int, int]] = [(0, 0)] * n
    while i < n:
        p = pieces[i]
        if p.oversize:
            out[i] = (p.start, p.end)
            i += 1
            continue
        j, total = i, p.tokens
        while (j + 1 < n and not pieces[j + 1].oversize and pieces[j + 1].heading == p.heading
               and total + pieces[j + 1].tokens <= max_tokens):
            j += 1; total += pieces[j].tokens
        span = (pieces[i].start, pieces[j].end)
        for k in range(i, j + 1):
            out[k] = span
        i = j + 1
    return out