# Stats

from dataclasses import dataclass

@dataclass
class EncodeStats:
    n_chunks: int
    seconds: float
    mean_sparse_nnz: float

    @property
    def chunks_per_s(self) -> float:
        return self.n_chunks / self.seconds if self.seconds > 0 else 0.0