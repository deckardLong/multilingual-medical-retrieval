# Define piece schema

from dataclasses import dataclass

# Define schema
@dataclass(frozen=True, slots=True)
class Piece:
    start: int
    end: int
    heading: str
    tokens: int
    oversize: bool = False