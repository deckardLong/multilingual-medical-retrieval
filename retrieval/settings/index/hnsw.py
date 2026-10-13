# Define HNSW schema

from common.config import Cfg

# Define class
class HnswCfg(Cfg):
    m: int
    ef_construct: int
    on_disk: bool