# Overisze => Recursive chunking

from langchain_text_splitters import RecursiveCharacterTextSplitter
from .greedy import GreedySplitter

def _first_nonspace(text: str, i: int, stop: int) -> int:
    while i < stop and text[i].isspace():
        i += 1
    return i

def _last_nonspace_end(text: str, start: int, end: int) -> int:
    while end > start and text[end - 1].isspace():
        end -= 1
    return end

class OversizeSplitter:
    """Chia một đoạn quá dài bằng RecursiveCharacterTextSplitter của LangChain, rồi quy về offset trong văn bản gốc
    (kết quả luôn là chuỗi con nguyên văn). Sau khi định vị luôn kiểm tra các mảnh phủ liền mạch; nếu có hở
    (nội dung lặp làm `find` định vị sai) thì dùng GreedySplitter (offset chính xác) cho đoạn này."""

    def __init__(self, cfg, counter):
        self.sp = RecursiveCharacterTextSplitter(
            chunk_size=cfg.chunk_size, chunk_overlap=cfg.chunk_overlap,
            separators=cfg.separators, length_function=counter.count,
            keep_separator=True, strip_whitespace=True)
        self.greedy = GreedySplitter(cfg, counter)

    def spans(self, text: str, start: int, end: int) -> list[tuple[int, int]]:
        spans = self._locate(text, start, end)
        if spans is None or not self._gap_free(text, spans, start, end):
            return self.greedy.spans(text, start, end)
        return spans

    def _locate(self, text: str, start: int, end: int) -> list[tuple[int, int]] | None:
        out, cursor = [], start
        for part in self.sp.split_text(text[start:end]):
            i = text.find(part, cursor, end)
            if i < 0:
                return None
            out.append((i, i + len(part)))
            cursor = i + 1                  # mảnh sau bắt đầu sau mảnh trước (có overlap)
        return out

    @staticmethod
    def _gap_free(text: str, spans: list[tuple[int, int]], start: int, end: int) -> bool:
        """Mảnh đầu bắt đầu ở ký tự không-trắng đầu tiên, mảnh cuối kết thúc ở ký tự không-trắng cuối cùng,
        mỗi mảnh sau tiến lên và bắt đầu không quá chỗ không-trắng kế tiếp sau mảnh trước (không hở)."""
        if not spans:
            return _first_nonspace(text, start, end) == end
        if spans[0][0] != _first_nonspace(text, start, end) or spans[-1][1] != _last_nonspace_end(text, start, end):
            return False
        return all(s1 > s0 and s1 <= _first_nonspace(text, e0, end) for (s0, e0), (s1, _) in zip(spans, spans[1:]))