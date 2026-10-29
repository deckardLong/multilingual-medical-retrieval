# Define rerank config schema

from typing import Literal
from pydantic import model_validator
from common.config import Cfg

# Define class
class RerankCfg(Cfg):
    enabled: bool
    backend: Literal["bge_reranker", "fake"]     # fake: chỉ cho test/dev không GPU
    model: str
    fp16: bool                                    # GPU chọn bằng CUDA_VISIBLE_DEVICES
    batch_size: int
    max_length: int                               # token của cặp (query, chunk) ghép lại
    query_mode: Literal["max_over_subqueries", "original"]
    top_n: int | None = None                      # chỉ rerank top_n chunk đầu của pool; phần sau giữ thứ tự hybrid

    @model_validator(mode="after")
    def _check(self):
        if self.batch_size <= 0 or self.max_length <= 0:
            raise ValueError("rerank.batch_size và max_length phải > 0")
        if self.top_n is not None and self.top_n <= 0:
            raise ValueError("rerank.top_n phải > 0 (hoặc null để rerank cả pool)")
        return self