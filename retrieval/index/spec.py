from qdrant_client import models as m
from .names import DENSE, SPARSE

def collection_kwargs(index_cfg, embed_cfg) -> dict:
    """Tham số create_collection, dựng thuần từ cấu hình (không gọi server)."""
    dense = m.VectorParams(
        size=embed_cfg.dim, distance=m.Distance.COSINE, on_disk=index_cfg.on_disk_vectors,
        hnsw_config=m.HnswConfigDiff(m=index_cfg.hnsw.m, ef_construct=index_cfg.hnsw.ef_construct,
                                     on_disk=index_cfg.hnsw.on_disk))
    kw: dict = dict(vectors_config={DENSE: dense}, on_disk_payload=index_cfg.on_disk_payload)
    if embed_cfg.use_sparse:
        kw["sparse_vectors_config"] = {SPARSE: m.SparseVectorParams(
            index=m.SparseIndexParams(on_disk=index_cfg.on_disk_vectors))}
    q = index_cfg.quantization
    if q.enabled:
        kw["quantization_config"] = m.ScalarQuantization(scalar=m.ScalarQuantizationConfig(
            type=m.ScalarType.INT8, quantile=q.quantile, always_ram=q.always_ram))
    return kw