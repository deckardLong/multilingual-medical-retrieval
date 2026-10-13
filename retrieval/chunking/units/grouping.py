# Group units

from .headings import is_heading
from .types import Piece

# Group units
def group_units(text: str, lines: list[tuple[int, int]], counts: list[int],
                heading_max_chars: int, target_tokens: int) -> list[Piece]:
    """Merge lines into units"""
    units: list[Piece] = []
    head, cur, used, only_head = "", [], 0, False

    # Flush
    def flush():
        nonlocal cur, used
        if cur:
            units.append(Piece(cur[0][0], cur[-1][1], head, used))
            cur, used = [], 0

    for (s, e), n in zip(lines, counts):
        ln = text[s:e]
        if is_heading(ln, heading_max_chars):
            if not only_head:
                flush()                     # prev unit uses old heading
            head = ln.strip()
            cur.append((s, e)); used += n
            only_head = True
            continue
        only_head = False
        if cur and used + n > target_tokens:
            flush()
        cur.append((s, e))
        used += n
    flush()
    return units