# Chunk shard

from dataclasses import dataclass
from pathlib import Path
from common.io import read_docs, write_chunks
from .validate import validate_doc_chunks

class ChunkingError(RuntimeError):
    pass

# Define shard stats
@dataclass
class ShardStats:
    n_docs: int = 0
    n_empty_docs: int = 0
    n_chunks: int = 0
    max_tokens: int = 0
    sum_tokens: int = 0

    @property
    def mean_tokens(self) -> float:
        return self.sum_tokens / self.n_chunks if self.n_chunks else 0.0

# Handle chunk shard
def chunk_shard(shard: Path, out: Path, chunker) -> ShardStats:
    """shard doc → parquet chunk. Lỗi offset ở bất kỳ doc nào thì dừng, không ghi file dở."""
    st, rows = ShardStats(), []
    for doc in read_docs(shard):
        chunks = chunker.split(doc)
        errs = validate_doc_chunks(doc, chunks)
        if errs:
            raise ChunkingError(f"{shard.name}/{doc.uid}: {errs[:3]}")
        st.n_docs += 1
        st.n_empty_docs += not chunks
        for c in chunks:
            st.n_chunks += 1; st.sum_tokens += c.n_tokens; st.max_tokens = max(st.max_tokens, c.n_tokens)
        rows += chunks
    write_chunks(rows, out)
    return st