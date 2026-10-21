import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from common.schema import SparseVec


@dataclass
class VectorBatch:
    ids: list[str]
    dense: np.ndarray               # (n, dim) float32
    sparse: list[SparseVec]


def vector_schema(dim: int) -> pa.Schema:
    return pa.schema([
        ("chunk_id", pa.string()),
        ("dense", pa.list_(pa.float16(), dim)),     # fp16: ~2 KB/chunk
        ("sp_idx", pa.list_(pa.int32())),
        ("sp_val", pa.list_(pa.float32())),
    ])


def write_vectors(path: Path, ids: list[str], dense: np.ndarray, sparse: list[SparseVec]) -> None:
    """Ghi nguyên tử (file tạm rồi đổi tên). dense: (n, dim)."""
    n, dim = dense.shape
    if not (len(ids) == n == len(sparse)):
        raise ValueError(f"độ dài lệch: ids={len(ids)} dense={n} sparse={len(sparse)}")
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    flat = pa.array(np.ascontiguousarray(dense, dtype=np.float16).ravel(), type=pa.float16())
    table = pa.table({
        "chunk_id": pa.array(ids, pa.string()),
        "dense": pa.FixedSizeListArray.from_arrays(flat, dim),
        "sp_idx": pa.array([s.indices for s in sparse], pa.list_(pa.int32())),
        "sp_val": pa.array([s.values for s in sparse], pa.list_(pa.float32())),
    }, schema=vector_schema(dim))
    tmp = path.with_suffix(".tmp")
    pq.write_table(table, tmp, compression="zstd")
    os.replace(tmp, path)


def _to_batch(t: pa.Table) -> VectorBatch:
    col = t.column("dense").combine_chunks()
    dim = col.type.list_size
    dense = np.asarray(col.values.to_numpy(zero_copy_only=False), dtype=np.float32).reshape(len(col), dim)
    sparse = [SparseVec(i, v) for i, v in zip(t.column("sp_idx").to_pylist(), t.column("sp_val").to_pylist())]
    return VectorBatch(t.column("chunk_id").to_pylist(), dense, sparse)


def iter_vectors(path: Path, batch_rows: int = 4096) -> Iterator[VectorBatch]:
    """Đọc từng lô để upsert mà không nạp cả shard vào RAM."""
    for rb in pq.ParquetFile(path).iter_batches(batch_size=batch_rows):
        yield _to_batch(pa.Table.from_batches([rb]))


def read_vectors(path: Path) -> VectorBatch:
    return _to_batch(pq.read_table(path))

def read_vector_ids(path: Path) -> list[str]:
    """Chỉ đọc cột chunk_id (rẻ): để kiểm tra khớp với shard chunk trước khi động vào index."""
    return pq.read_table(path, columns=["chunk_id"]).column("chunk_id").to_pylist()

def merge_vector_parts(parts: list[Path], out_path: Path) -> int:
    """Nối các file vector cùng schema thành một file, ghi nguyên tử và theo luồng (không nạp cả shard vào RAM).
    Trả số dòng đã ghi. Danh sách rỗng là lỗi: chỗ gọi phải tự ghi file rỗng vì ở đây không biết `dim`."""
    if not parts:
        raise ValueError("không có part nào để gộp")
    out_path = Path(out_path); out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp, n, writer = out_path.with_suffix(".tmp"), 0, None
    try:
        for p in parts:
            f = pq.ParquetFile(p)
            if writer is None:
                writer = pq.ParquetWriter(tmp, f.schema_arrow, compression="zstd")
            for rb in f.iter_batches(batch_size=4096):
                writer.write_table(pa.Table.from_batches([rb]))
                n += rb.num_rows
    finally:
        if writer is not None:
            writer.close()
    os.replace(tmp, out_path)
    return n