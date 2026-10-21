from pathlib import Path
from pydantic import field_validator
from common.config import Cfg


class BuildCfg(Cfg):
    max_docs: int | None
    max_chunks: int | None

    @field_validator("max_docs", "max_chunks")
    @classmethod
    def _positive(cls, v):
        if v is not None and v <= 0:
            raise ValueError("phải > 0 (hoặc null để không giới hạn)")
        return v


class CheckCfg(Cfg):
    btc_ids_path: Path | None
    max_chunk_tokens: int
    token_counter: str

    @field_validator("max_chunk_tokens")
    @classmethod
    def _positive(cls, v):
        if v <= 0:
            raise ValueError("max_chunk_tokens phải > 0")
        return v


class SubmitCfg(Cfg):
    candidates_path: Path
    output_dir: Path
    json_name: str
    build: BuildCfg
    check: CheckCfg
    log_csv: Path

    @field_validator("json_name")
    @classmethod
    def _plain_json_name(cls, v):
        if "/" in v or "\\" in v or not v.endswith(".json"):
            raise ValueError("json_name phải là tên file .json, không có thư mục (zip chỉ chứa một file ở gốc)")
        return v