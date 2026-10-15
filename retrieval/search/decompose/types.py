from dataclasses import dataclass

@dataclass(frozen=True)
class Decomposed:
    original: str
    queries: list[str]          # các truy vấn dùng để TÌM KIẾM (theo keep_original)
    subs: list[str]             # các truy vấn con tách được (rỗng nếu không tách)

    @property
    def rerank_queries(self) -> list[str]:
        """Truy vấn gốc luôn đứng đầu (reranker dùng queries[0] khi query_mode=original)."""
        return [self.original, *self.subs]