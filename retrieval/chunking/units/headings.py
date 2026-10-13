# Check whether it's heading

import re

# END & SKIP
_END = re.compile(r"[.!?:;,…”\"')\]。！？：；，、）】》]$")

_SKIP = re.compile(r"(Ảnh:|\(Nguồn:|Nguồn ảnh|图片来源|来源：)|^Theo ")

# Is heading
def is_heading(line: str, max_chars: int) -> bool:
    ln = line.strip()
    return bool(ln) and len(ln) < max_chars and not _END.search(ln) and not _SKIP.search(ln)