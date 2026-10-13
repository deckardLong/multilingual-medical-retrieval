# Decompose query to subqueries

from typing import Literal
from common.config import Cfg

# Define class
class DecomposeCfg(Cfg):
    mode: Literal["off", "rule", "llm"]
    max_subqueries: int
    keep_original: bool