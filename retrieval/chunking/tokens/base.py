# Define token counter schema

from typing import Protocol

# Schema
class TokenCounter(Protocol):
    def count(self, text: str) -> int:
        ...

    def count_many(self, texts: list[str]) -> list[int]:
        ...