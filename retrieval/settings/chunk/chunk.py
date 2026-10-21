# Define chunk config schema

from typing import Literal
from pydantic import model_validator
from common.config import Cfg
from .structure import StructureCfg
from .recursive import RecursiveCfg
from .parent import ParentCfg

# Define class
class ChunkCfg(Cfg):
    version: int
    method: Literal["structure", "recursive"]
    tokenizer: str
    contextual_prefix: bool
    ctx_margin_tokens: int
    min_chunk_tokens: int
    structure: StructureCfg
    recursive: RecursiveCfg
    parent: ParentCfg

    @model_validator(mode="after")
    def _check(self):
        if self.parent.enabled and self.parent.max_tokens < self.structure.hard_tokens:
            raise ValueError("parent.max_tokens phải >= structure.hard_tokens")
        return self

    # Define ver
    @property
    def ver(self) -> str:
        return f"{self.method}-v{self.version}"

    # Max tokens
    @property
    def max_tokens(self) -> int:
        """The max tokens of 1 chunk""" 
        if self.method == "recursive":
            return self.recursive.chunk_size
        return max(self.structure.hard_tokens, self.recursive.chunk_size)