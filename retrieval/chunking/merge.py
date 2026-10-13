# Merge short lines

from .units import Piece

# Join
def _join(a: Piece, b: Piece) -> Piece:
    return Piece(a.start, b.end, a.heading, a.tokens + b.tokens)

# Fits
def _fits(a: Piece, b: Piece, hard: int) -> bool:
    return not a.oversize and not b.oversize and a.tokens + b.tokens <= hard

# Merge short
def merge_short(pieces: list[Piece], min_tokens: int, hard_tokens: int) -> list[Piece]:
    out: list[Piece] = []
    for p in pieces:
        if (out and out[-1].heading == p.heading and (out[-1].tokens < min_tokens or p.tokens < min_tokens)
                and _fits(out[-1], p, hard_tokens)):
            out[-1] = _join(out[-1], p)
        else:
            out.append(p)
    if len(out) >= 2 and out[-1].tokens < min_tokens and _fits(out[-2], out[-1], hard_tokens):
        last = out.pop()
        out[-1] = _join(out[-1], last)
    return out