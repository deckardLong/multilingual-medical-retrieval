from qdrant_client import models as m
from common.io import VectorBatch
from .errors import IndexingError
from .ids import point_id
from .names import DENSE, SPARSE

def build_points(vb: VectorBatch, cols: dict[str, list], pos: dict[str, int],
                 payload_fields: list[str], use_sparse: bool) -> list[m.PointStruct]:
    """Một lô vector + payload (lấy từ shard chunk theo chunk_id, không phụ thuộc thứ tự hai file)."""
    pts = []
    for i, cid in enumerate(vb.ids):
        j = pos.get(cid)
        if j is None:
            raise IndexingError(f"vector của {cid} không có trong shard chunk")
        vec: dict = {DENSE: vb.dense[i].tolist()}
        sv = vb.sparse[i]
        if use_sparse and sv.indices:               # sparse rỗng thì bỏ
            vec[SPARSE] = m.SparseVector(indices=list(sv.indices), values=list(sv.values))
        pts.append(m.PointStruct(id=point_id(cid), vector=vec, payload={f: cols[f][j] for f in payload_fields}))
    return pts