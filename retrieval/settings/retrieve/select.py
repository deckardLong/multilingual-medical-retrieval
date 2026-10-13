# Define selection schema

from common.config import Cfg

# Define class
class SelectCfg(Cfg):
    max_docs: int
    min_score: float | None
    rel_drop: float | None
    chunks_per_doc: int