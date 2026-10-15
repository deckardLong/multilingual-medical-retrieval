import re

_UNIT = re.compile(r"[一-鿿]|\w+")
# kết thúc câu hỏi / ý: ?, ;, xuống dòng, dấu chấm câu Trung; KHÔNG tách ở dấu chấm vì hay là viết tắt (TS., BS.)
_SENT = re.compile(r"[?？;；。\n]+")
# liên từ nối hai ý độc lập; "和/与/及" trong tiếng Trung hay nối danh từ nên không tách theo chúng
_CONJ = re.compile(r"\s+(?:và cả|và|cũng như|đồng thời|and|as well as)\s+|(?:以及|并且|同时|还有|而且)", re.IGNORECASE)

def count_units(text: str) -> int:
    """Số từ (chữ Latin) + số chữ Hán: thước đo độ dài không cần tokenizer."""
    return len(_UNIT.findall(text))

def split_questions(text: str) -> list[str]:
    return [p.strip(" ,.:-–•\t") for p in _SENT.split(text) if p.strip(" ,.:-–•\t")]

def split_conjunction(sentence: str, min_units: int) -> list[str]:
    """Tách theo liên từ CHỈ KHI mọi vế đều đủ dài (tất cả hoặc không gì cả)."""
    parts = [p.strip(" ,.:-–") for p in _CONJ.split(sentence)]
    parts = [p for p in parts if p]
    if len(parts) < 2 or any(count_units(p) < min_units for p in parts):
        return [sentence]
    return parts