# Define recursive config schema

from pydantic import model_validator
from common.config import Cfg

# Define class
class RecursiveCfg(Cfg):
    chunk_size: int
    chunk_overlap: int
    separators: list[str]

    @model_validator(mode="after")
    def _check(self):
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("recursive.chunk_overlap phải nhỏ hơn chunk_size")
        return self