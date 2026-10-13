# Define rerank config schema

from typing import Literal
from common.config import Cfg

# Define class
class RerankCfg(Cfg):
    enabled: bool
    model: str
    device: str
    fp16: bool
    batch_size: int
    max_length: int
    query_mode: Literal["max_over_subqueries", "original"]