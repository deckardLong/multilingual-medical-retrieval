from .types import Decomposed

class IdentityDecomposer:
    """decompose.mode=off: chỉ dùng truy vấn gốc."""

    def decompose(self, query: str) -> Decomposed:
        return Decomposed(query, [query], [])