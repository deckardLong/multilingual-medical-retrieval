# Define embedding config schema

from typing import ClassVar, Literal
from pydantic import model_validator
from common.config import Cfg

# Define class
class EmbedCfg(Cfg):
   
    # Speed
    HASH_EXCLUDE: ClassVar[frozenset[str]] = frozenset({
        "batch_size", "slice_size", "query_max_length"
    })
    backend: Literal["bge_m3", "fake"]
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
    query_prompt: str = ""
    doc_prompt: str = ""

    @model_validator(mode="after")
    def _check(self):
        if self.backend == "st_dense" and self.use_sparse:
            raise ValueError("backend st_dense chỉ có dense: đặt use_sparse = false")
        if self.query_max_length > self.max_length:
            raise ValueError("query_max_length không được lớn hơn max_length")
        return self

    @property
    def ver(self) -> str:
        return f"{self.name}-v{self.version}"