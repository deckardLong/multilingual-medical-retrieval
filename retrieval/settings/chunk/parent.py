# Define parent schema

from pydantic import model_validator
from common.config import Cfg

# Define max chunk tokens
BTC_MAX_CHUNK_TOKENS = 1024

# Define class
class ParentCfg(Cfg):
    enabled: bool
    max_tokens: int

    @model_validator(mode="after")
    def _check(self):
        if self.max_tokens > BTC_MAX_CHUNK_TOKENS:
            raise ValueError (f"parent.max_tokens > {BTC_MAX_CHUNK_TOKENS} (giới hạn khuyến nghị của bên BTC)")
        return self