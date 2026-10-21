from pydantic import field_validator
from common.config import Cfg


class SyncCfg(Cfg):
    repo_id: str
    repo_type: str
    revision: str
    allow_patterns: list[str]
    max_workers: int

    @field_validator("repo_id", "revision")
    @classmethod
    def _nonblank(cls, v):
        if not v.strip():
            raise ValueError("không được rỗng")
        return v

    @field_validator("allow_patterns")
    @classmethod
    def _nonempty(cls, v):
        if not v:
            raise ValueError("allow_patterns không được rỗng (không có gì để tải)")
        return v

    @field_validator("max_workers")
    @classmethod
    def _positive(cls, v):
        if v <= 0:
            raise ValueError("max_workers phải > 0")
        return v