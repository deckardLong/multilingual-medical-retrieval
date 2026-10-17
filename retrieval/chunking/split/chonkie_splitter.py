from chonkie import RecursiveChunker
from .oversize import OversizeSplitter


class ChonkieSplitter:
    """Thay thế OversizeSplitter: Chonkie trả sẵn offset nguyên văn (không cần tìm lại).
    Hạn chế đã biết: không có chunk_overlap; và khi truyền hàm đếm token (callable) nó không cắt được
    đoạn KHÔNG có dấu ngắt nào (NotImplementedError) → khi đó dùng lại OversizeSplitter cho đoạn đó."""

    def __init__(self, cfg, counter):
        self.ck = RecursiveChunker(tokenizer=counter.count, chunk_size=cfg.chunk_size)
        self.fallback = OversizeSplitter(cfg, counter)

    def spans(self, text: str, start: int, end: int) -> list[tuple[int, int]]:
        try:
            return [(start + c.start_index, start + c.end_index) for c in self.ck.chunk(text[start:end])]
        except NotImplementedError:
            return self.fallback.spans(text, start, end)