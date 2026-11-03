"""Cắt chunk thành các đoạn ngắn theo câu. BTC tính một chunk là khớp khi phần chung (LCS) chiếm >= 40% cả đoạn đáp án
lẫn chunk dự đoán, nên một đoạn dài w từ chỉ khớp được đáp án dài khoảng 0,4w–2,5w; chunk dài trượt khi đáp án ngắn.
Mỗi đoạn là chuỗi con nguyên văn của chunk (giữ đúng yêu cầu trích từ tài liệu gốc)."""
import re

_CJK = "㐀-䶿一-鿿豈-﫿"
_UNIT = re.compile(rf"[{_CJK}]|[^\s{_CJK}]+")        # chữ Hán tính từng chữ, chữ khác tính theo từ
_SENT_END = re.compile(r"[.!?;:。！？；：…]['\")\]”’]*$")
MIN_UNITS = 5


def _sentences(text: str) -> list[list[re.Match]]:
    sents, cur, last_end = [], [], 0
    for m in _UNIT.finditer(text):
        if cur and "\n" in text[last_end:m.start()]:
            sents.append(cur); cur = []
        cur.append(m)
        last_end = m.end()
        if _SENT_END.search(m.group()):
            sents.append(cur); cur = []
    if cur:
        sents.append(cur)
    return sents


def split_text(text: str, max_units: int) -> list[str]:
    """Gộp câu liền nhau thành đoạn <= max_units đơn vị; câu dài hơn thì cắt cứng. Đoạn quá ngắn gộp vào đoạn trước."""
    windows: list[list[re.Match]] = []
    cur: list[re.Match] = []
    for sent in _sentences(text):
        for start in range(0, len(sent), max_units):
            piece = sent[start:start + max_units]
            if cur and len(cur) + len(piece) > max_units:
                windows.append(cur); cur = []
            cur += piece
    if cur:
        windows.append(cur)
    merged: list[list[re.Match]] = []
    for w in windows:
        if merged and len(w) < MIN_UNITS:
            merged[-1] = merged[-1] + w
        else:
            merged.append(w)
    if len(merged) > 1 and len(merged[0]) < MIN_UNITS:
        merged[1] = merged[0] + merged[1]; merged.pop(0)
    return [text[w[0].start():w[-1].end()] for w in merged]
