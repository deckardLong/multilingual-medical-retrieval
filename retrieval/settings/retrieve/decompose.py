# Decompose query to subqueries

from typing import Literal
from pydantic import model_validator
from common.config import Cfg

class DecomposeCfg(Cfg):
    mode: Literal["off", "rule"]       # rule: tách theo dấu hỏi/chấm phẩy/liên từ
    max_subqueries: int
    keep_original: bool                # giữ truy vấn gốc trong danh sách tìm kiếm
    min_part_tokens: int = 4           # mỗi vế sau khi tách theo liên từ phải dài ít nhất ngần này từ/chữ Hán

    @model_validator(mode="after")
    def _check(self):
        if self.max_subqueries < 1 or self.min_part_tokens < 1:
            raise ValueError("decompose.max_subqueries và min_part_tokens phải >= 1")
        return self