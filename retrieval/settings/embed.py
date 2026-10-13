# Define embedding config schema

from typing import ClassVar
from common.config import Cfg

# Define class
class EmbedCfg(Cfg):
   
    # Speed
    HASH_EXCLUDE: ClassVar[frozenset[str]] = frozenset({
        "batch_size", "slice_size", "query_max_length"
    })
    name: str
    version: int
    model: str
    fp16: bool
    max_length: int
    dim: int
    use_sparse: bool
    batch_size: int
    slice_size: int
    query_max_length: int

    @property
    def ver(self) -> str:
        return f"{self.name}-v{self.version}"