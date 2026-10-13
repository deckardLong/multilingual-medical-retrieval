# Define structure of chunking schema

from pydantic import model_validator
from common.config import Cfg

# Define class
class StructureCfg(Cfg):
    target_tokens: int
    hard_tokens: int
    heading_max_chars: int

    @model_validator(mode="after")  # run after validating all fields
    def _check(self):
        if self.target_tokens >= self.hard_tokens:
            raise ValueError("structure.target_tokens phải nhỏ hơn hard_tokens")
        return self