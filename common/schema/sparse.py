# Define sparse vector class

from dataclasses import dataclass

# Define class
@dataclass(frozen=True, slots=True)
class SparseVec:
    indices: list[int]
    values: list[float]