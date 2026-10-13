# Handle lines

import re

# Define line
_LINE = re.compile(r"[^\n]+")

# Non blank
def _nonblank(text: str):
    return [m for m in _LINE.finditer(text) if m.group().strip()]

# Title end
def title_end(text: str) -> int:
    ms = _nonblank(text)
    return ms[0].end() if ms else 0

# Body lines
def body_lines(text: str) -> list[tuple[int, int]]:
    """Get body by index (not title)"""
    return [(m.start(), m.end()) for m in _nonblank(text)[1:]]