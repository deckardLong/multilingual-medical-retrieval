from dataclasses import dataclass
from pathlib import Path
from qdrant_client import models as m
from common.io import read_chunk_columns, iter_vectors, read_vector_ids
from .errors import IndexingError
from .filters import uid_filter, uid_batches
from .points import build_points

@dataclass
class UpsertStats:
    n_points: int
    n_docs: int

def delete_uids(client, collection: str, uids: list[str]) -> None:
    for b in uid_batches(uids):
        client.delete(collection, points_selector=m.FilterSelector(filter=uid_filter(b)), wait=True)

def count_uids(client, collection: str, uids: list[str]) -> int:
    return sum(client.count(collection, count_filter=uid_filter(b), exact=True).count for b in uid_batches(uids))

def upsert_shard(client, collection: str, chunks_path: Path, vectors_path: Path, index_cfg, *,
                 use_sparse: bool, verify: bool = True) -> UpsertStats:
    """Đưa một shard vào Qdrant. Idempotent: xóa mọi điểm của các doc (uid) trong shard rồi chèn lại,
    nên doc đổi nội dung / ít chunk hơn không để lại điểm cũ. Kiểm tra khớp TRƯỚC khi xóa."""
    fields = sorted(set(index_cfg.payload_fields) | {"chunk_id", "uid"})
    cols = read_chunk_columns(chunks_path, fields)
    pos = {cid: i for i, cid in enumerate(cols["chunk_id"])}
    vec_ids = read_vector_ids(vectors_path)
    if len(vec_ids) != len(pos) or set(vec_ids) != set(pos):
        raise IndexingError(f"{vectors_path.name}: chunk_id không khớp với {chunks_path.name} "
                            f"({len(vec_ids)} vector / {len(pos)} chunk)")
    uids = sorted(set(cols["uid"]))
    delete_uids(client, collection, uids)
    n = 0
    for vb in iter_vectors(vectors_path, index_cfg.upsert_batch):
        pts = build_points(vb, cols, pos, index_cfg.payload_fields, use_sparse)
        client.upsert(collection, pts, wait=True)
        n += len(pts)
    if verify:
        got = count_uids(client, collection, uids)
        if got != n:
            raise IndexingError(f"{chunks_path.name}: đã ghi {n} điểm nhưng Qdrant đếm được {got}")
    return UpsertStats(n, len(uids))