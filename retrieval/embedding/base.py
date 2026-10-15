# Define class Embedder

from typing import Protocol
from .types import Encoded

# Define class
class Embedder:
    dim: int

    # Encode docs
    def encode_docs(self, texts: list[str]) -> Encoded:
        ...

    # Encode queries
    def encode_queries(self, texts: list[str]) -> Encoded:
        ...