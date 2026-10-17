import re

_WORD = re.compile(r"\S+")

class GreedySplitter:
    """Phương án cuối cùng, offset tính CHÍNH XÁC (không phải tìm lại): gom từng từ (theo khoảng trắng) liên tiếp
    đến khi gần đủ chunk_size token. Từ nào tự nó đã quá dài (vd tiếng Trung không có khoảng trắng) thì tách
    từng ký tự. Không overlap, không theo ngữ nghĩa; chỉ dùng khi bộ chia chính cho kết quả có khoảng hở."""

    BUDGET = 0.9           # chừa chỗ vì số token của chuỗi ghép có thể lệch tổng token từng phần

    def __init__(self, cfg, counter):
        self.size, self.counter = max(1, int(cfg.chunk_size * self.BUDGET)), counter

    def _units(self, text: str, start: int, end: int) -> list[tuple[int, int]]:
        units: list[tuple[int, int]] = []
        for m in _WORD.finditer(text, start, end):
            a, b = m.span()
            if self.counter.count(text[a:b]) > self.size:
                units += [(i, i + 1) for i in range(a, b)]
            else:
                units.append((a, b))
        return units

    def spans(self, text: str, start: int, end: int) -> list[tuple[int, int]]:
        units = self._units(text, start, end)
        counts = self.counter.count_many([text[a:b] for a, b in units])
        out: list[tuple[int, int]] = []
        cur_s = cur_e = -1
        used = 0
        for (a, b), n in zip(units, counts):
            if cur_s >= 0 and used + n > self.size:
                out.append((cur_s, cur_e)); cur_s, used = -1, 0
            if cur_s < 0:
                cur_s = a
            cur_e, used = b, used + n
        if cur_s >= 0:
            out.append((cur_s, cur_e))
        return out