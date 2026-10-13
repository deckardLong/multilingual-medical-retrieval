# Define search schema

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