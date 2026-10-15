# Define types
from dataclasses import dataclass
import numpy as np
from common.schema import SparseVec

# Define dataclass
@dataclass
class Encoded:
    dense: np.ndarray
    sparse: list[SparseVec]