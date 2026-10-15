import time
from pathlib import Path
import numpy as np
from common.io import read_chunk_columns, write_vectors
from .batching import slices
from .stats import EncodeStats
from .texts import chunk_texts
from .validate import validate_encoded

def encode_shard(chunks_path: Path, out_path: Path, embedder, cfg) -> EncodeStats:
    """parquet chunk → parquet vector. Mỗi lát được kiểm tra trước khi ghi; lỗi thì không ghi file dở."""
    cols = read_chunk_columns(chunks_path, ["chunk_id", "ctx", "text"])
    ids, texts = cols["chunk_id"], chunk_texts(cols["ctx"], cols["text"])
    dense_parts, sparse = [], []
    t0 = time.perf_counter()
    for a, b in slices(len(texts), cfg.slice_size):
        enc = embedder.encode_docs(texts[a:b])
        validate_encoded(enc, b - a, cfg.dim, use_sparse=cfg.use_sparse)
        dense_parts.append(enc.dense.astype(np.float16))
        sparse += enc.sparse
    dense = np.concatenate(dense_parts) if dense_parts else np.zeros((0, cfg.dim), np.float16)
    write_vectors(out_path, ids, dense, sparse)
    nnz = sum(len(s.indices) for s in sparse) / len(sparse) if sparse else 0.0
    return EncodeStats(len(ids), time.perf_counter() - t0, nnz)