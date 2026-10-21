from qdrant_client import models as m
from common.schema import Candidate, SparseVec
from retrieval.index import DENSE, SPARSE
from .filters import lang_filter
from .hits import hit_to_candidate

QueryVec = tuple[list[float], SparseVec | None]


class HybridSearcher:
    """Toàn bộ hybrid chạy TRONG Qdrant bằng một lệnh query_points (prefetch lồng nhau):
        mỗi truy vấn con: dense (k_dense) + sparse (k_sparse) → RRF → k_fuse
        rồi RRF giữa các truy vấn con (hằng số rrf_k) → k_pool."""

    def __init__(self, client, collection: str, search_cfg, payload_fields: list[str]):
        self.client, self.collection, self.cfg, self.fields = client, collection, search_cfg, payload_fields
        self.filter = lang_filter(search_cfg.langs)

    def _one(self, dense: list[float], sparse: SparseVec | None) -> m.Prefetch:
        c = self.cfg
        params = m.SearchParams(hnsw_ef=c.hnsw_ef,
                                quantization=m.QuantizationSearchParams(rescore=c.rescore, oversampling=c.oversampling))
        branches = [m.Prefetch(query=dense, using=DENSE, limit=c.k_dense, filter=self.filter, params=params)]
        if sparse is not None and sparse.indices:
            branches.append(m.Prefetch(query=m.SparseVector(indices=list(sparse.indices), values=list(sparse.values)),
                                       using=SPARSE, limit=c.k_sparse, filter=self.filter))
        return m.Prefetch(prefetch=branches, query=m.FusionQuery(fusion=m.Fusion.RRF), limit=c.k_fuse)

    def search(self, vectors: list[QueryVec]) -> list[Candidate]:
        """vectors: (dense, sparse) của từng truy vấn tìm kiếm (truy vấn gốc + các truy vấn con)."""
        c = self.cfg
        res = self.client.query_points(
            self.collection, prefetch=[self._one(d, s) for d, s in vectors],
            query=m.RrfQuery(rrf=m.Rrf(k=c.rrf_k)), limit=c.k_pool, with_payload=self.fields)
        return [hit_to_candidate(h) for h in res.points]