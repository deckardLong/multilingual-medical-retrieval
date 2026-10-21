import time
from pathlib import Path
from typing import Callable

import numpy as np
from common.io import file_fingerprint, read_chunk_columns
from retrieval.progress import quiet_tqdm
from .batching import slices
from .checkpoint import open_checkpoint
from .stats import EncodeStats
from .texts import chunk_texts
from .validate import validate_encoded


def encode_shard(chunks_path: Path, out_path: Path, embedder, cfg, *,
                 on_progress: Callable[[int], None] | None = None, resume: bool = True) -> EncodeStats:
    """parquet chunk → parquet vector. Mỗi lát được kiểm tra rồi ghi ngay thành một part, nên lần chạy sau
    tiếp tục được từ chỗ dở (resume=False để ép làm lại từ đầu). File vector cuối chỉ xuất hiện khi shard
    đã xong trọn vẹn — stage sau không bao giờ thấy file dở.

    `mean_sparse_nnz` chỉ tính trên phần mã hoá TRONG LẦN CHẠY NÀY (phần resume lại từ trước không đọc lại)."""
    cols = read_chunk_columns(chunks_path, ["chunk_id", "ctx", "text"])
    ids, texts = cols["chunk_id"], chunk_texts(cols["ctx"], cols["text"])
    n = len(ids)
    ck = open_checkpoint(out_path, file_fingerprint(chunks_path), n)
    if not resume and ck.resumed:
        ck.discard()
        ck = open_checkpoint(out_path, file_fingerprint(chunks_path), n)
    if on_progress and ck.done:
        on_progress(ck.done)                                   # phần làm từ lần trước vẫn phải tính vào thanh

    sparse_nnz, sparse_n, t0 = 0, 0, time.perf_counter()
    for a, b in slices(n, cfg.slice_size, start=ck.done):
        with quiet_tqdm():                                     # model không được vẽ thanh riêng đè lên thanh chính
            enc = embedder.encode_docs(texts[a:b])
        validate_encoded(enc, b - a, cfg.dim, use_sparse=cfg.use_sparse)
        ck.write_part(ids[a:b], enc.dense.astype(np.float16), enc.sparse)
        sparse_nnz += sum(len(s.indices) for s in enc.sparse)
        sparse_n += len(enc.sparse)
        if on_progress:
            on_progress(b - a)
    ck.merge_into(out_path, cfg.dim)
    return EncodeStats(n, time.perf_counter() - t0, sparse_nnz / sparse_n if sparse_n else 0.0)