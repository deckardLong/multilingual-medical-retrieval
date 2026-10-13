# Define index schema

from typing import ClassVar
from pydantic import model_validator
from common.config import Cfg
from .hnsw import HnswCfg
from .quantization import QuantizationCfg

# Define required payload
REQUIRED_PAYLOAD = {
    "chunk_id", "uid", "start", "end", "text"
}

# Define class
class IndexCfg(Cfg):
    HASH_EXCLUDE: ClassVar[frozenset[str]] = frozenset({
        "alias", "upsert_batch"
    })
    collection_prefix: str
    alias: str
    on_disk_vectors: bool
    on_disk_payload: bool
    payload_fields: list[str]
    payload_indexes: list[str]
    hnsw: HnswCfg
    quantization: QuantizationCfg
    upsert_batch: int

    @model_validator(mode="after")
    def _check(self):
        miss = REQUIRED_PAYLOAD - set(self.payload_fields)
        if miss:
            raise ValueError(f"index.payload_fields thiếu: {sorted(miss)}")
        return self