# Package all retrieval + hash configs, version tags, and dir

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from common.config import Env, sha
from .chunk import ChunkCfg
from .embed import EmbedCfg
from .index import IndexCfg
from .retrieve import RetrieveCfg
from .rerank import RerankCfg

# Define dataclass
@dataclass(frozen=True)
class RetrievalSettings:
    # ====== Configuration ======
    env: Env
    chunk: ChunkCfg
    embed: EmbedCfg
    index: IndexCfg
    retrieve: RetrieveCfg
    rerank: RerankCfg
    h_chunk: str
    h_embed: str
    h_index: str

    # ====== Tags ======
    @property
    def chunk_tag(self) -> str: 
        return f"{self.chunk.ver}-{self.h_chunk[:6]}"
    @property
    def embed_tag(self) -> str: 
        return f"{self.embed.ver}-{self.h_embed[:6]}"
    @property
    def collection(self) -> str: 
        return f"{self.index.collection_prefix}__{self.embed_tag}__{self.h_index[:4]}"

    # ====== Dirs ======
    @property
    def chunks_dir(self) -> Path: 
        return self.env.r2ai_derived_dir / "chunks" / self.chunk_tag
    @property
    def vectors_dir(self) -> Path: 
        return self.env.r2ai_derived_dir / "vectors" / self.embed_tag
    @property
    def manifest_path(self) -> Path: 
        return self.env.r2ai_state_dir / "retrieval" / "manifest.jsonl"

    # Run ID
    def run_id(self) -> str:
        q = sha([self.retrieve.model_dump(mode="json"), self.rerank.model_dump(mode="json")])[:4]
        exp = self.env.r2ai_experiment or "base"
        return f"{datetime.now():%Y%m%d-%H%M}_{exp}_{self.h_index[:4]}{q}"

    def pool_key(self) -> str:
        """Dấu vân tay của mọi thứ ảnh hưởng tới pool (không gồm select, vì chọn diễn ra sau): dùng để nối tiếp lượt chạy dở."""
        r = self.retrieve
        d = lambda c: c.model_dump(mode="json")
        return sha([self.collection, d(r.decompose), d(r.search), d(self.rerank)])

    # Run card
    def run_card(self) -> dict:
        d = lambda c: c.model_dump(mode="json")
        return {
            "experiment": self.env.r2ai_experiment, 
            "collection": self.collection,
            "chunk_tag": self.chunk_tag, 
            "embed_tag": self.embed_tag,
            "hashes": {
                "chunk": self.h_chunk, 
                "embed": self.h_embed, 
                "index": self.h_index
            },
            "chunk": d(self.chunk), 
            "embed": d(self.embed), 
            "index": d(self.index),
            "retrieve": d(self.retrieve), 
            "rerank": d(self.rerank)
        }