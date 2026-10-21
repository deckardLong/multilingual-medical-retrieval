# Define selection schema

from pydantic import model_validator
from common.config import Cfg

# Define class
class SelectCfg(Cfg):
    max_docs: int
    min_score: float | None
    rel_drop: float | None
    chunks_per_doc: int

    @model_validator(mode="after")
    def _check(self):
        if self.max_docs < 1 or self.chunks_per_doc < 1:
            raise ValueError("select.max_docs và chunks_per_doc phải >= 1")
        if self.min_score is not None and not 0 <= self.min_score <= 1:
            raise ValueError("select.min_score phải nằm trong [0, 1]")
        if self.rel_drop is not None and not 0 < self.rel_drop <= 1:
            raise ValueError("select.rel_drop phải nằm trong (0, 1]")
        return self