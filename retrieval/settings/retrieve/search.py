# Define search schema

from pydantic import model_validator
from common.config import Cfg

# Define class
class SearchCfg(Cfg):
    k_dense: int
    k_sparse: int
    k_fuse: int
    k_pool: int
    rrf_k: int
    langs: list[str] | None
    hnsw_ef: int
    rescore: bool
    oversampling: float

    @model_validator(mode="after")
    def _check(self):
        for field in ("k_dense", "k_sparse", "k_fuse", "k_pool", "rrf_k", "hnsw_ef"):
            if getattr(self, field) < 1:
                raise ValueError(f"search.{field} phải >= 1")
        if self.oversampling < 1:
            raise ValueError("search.oversampling phải >= 1")
        return self