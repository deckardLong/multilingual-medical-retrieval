from typing import Protocol

class PairScorer(Protocol):
    """Chấm điểm các cặp (query, passage) → điểm trong [0, 1], cao = liên quan hơn."""

    def score_pairs(self, pairs: list[tuple[str, str]]) -> list[float]: 
        ...