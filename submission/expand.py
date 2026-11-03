"""Nới chunk thành cửa sổ dài hơn quanh đúng vị trí của nó trong tài liệu gốc (theo câu), để độ dài gần với đáp án của BTC.
Cửa sổ là doc.text[a:b] nguyên văn nên vẫn là trích đoạn từ tài liệu gốc."""
import io
import json
from pathlib import Path
from typing import Iterable
import zstandard
from .split import _sentences


def load_texts(docs_dir: Path, uids: set[str]) -> dict[str, str]:
    texts: dict[str, str] = {}
    for path in sorted(Path(docs_dir).glob("*/*.jsonl.zst")):
        with open(path, "rb") as f, zstandard.ZstdDecompressor().stream_reader(f) as r:
            for line in io.TextIOWrapper(r, encoding="utf-8"):
                if not line.strip():
                    continue
                d = json.loads(line)
                if d.get("uid") in uids:
                    texts[d["uid"]] = d["text"]
    return texts


def sentence_spans(text: str) -> list[tuple[int, int, int]]:
    """(start, end, số đơn vị) của từng câu; chữ Hán tính từng chữ, chữ khác tính theo từ."""
    return [(s[0].start(), s[-1].end(), len(s)) for s in _sentences(text)]


def widen(spans: list[tuple[int, int, int]], start: int, end: int, target: int) -> tuple[int, int]:
    """Mở rộng [start, end) ra các câu kề hai bên (luân phiên sau/trước) tới khi đủ khoảng target đơn vị. Không thu ngắn chunk."""
    inside = [i for i, (a, b, _) in enumerate(spans) if a < end and b > start]
    if not inside:
        return start, end
    lo, hi = inside[0], inside[-1]
    units = sum(spans[i][2] for i in range(lo, hi + 1))
    grew = True
    while grew and units < target:
        grew = False
        for j in (hi + 1, lo - 1):
            if 0 <= j < len(spans) and units + spans[j][2] <= target:
                lo, hi = min(lo, j), max(hi, j)
                units += spans[j][2]
                grew = True
    return min(start, spans[lo][0]), max(end, spans[hi][1])


class Expander:
    def __init__(self, texts: dict[str, str], target: int):
        self.texts, self.target = texts, target
        self._spans: dict[str, list[tuple[int, int, int]]] = {}

    def window(self, uid: str, start: int, end: int) -> tuple[int, int, str] | None:
        text = self.texts.get(uid)
        if text is None:
            return None
        if uid not in self._spans:
            self._spans[uid] = sentence_spans(text)
        a, b = widen(self._spans[uid], start, end, self.target)
        return a, b, text[a:b].strip()


def needed_uids(results: Iterable) -> set[str]:
    return {c.uid for r in results for c in r.candidates}
