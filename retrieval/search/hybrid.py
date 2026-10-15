from qdrant_client import models as m
from common.schema import Candidate, SparseVec
from retrieval.index import DENSE, SPARSE
from .filters import lang_filter
from .hits import hit_to_candidate


class HybridSearcher:
    """Một truy vấn: dense + sparse (mỗi nhánh lấy k riêng) rồi Qdrant hợp nhất bằng RRF."""

    def __init__(self, client, collection: str, search_cfg, payload_fields: list[str]):
        self.client, self.collection, self.cfg, self.fields = client, collection, search_cfg, payload_fields
        self.filter = lang_filter(search_cfg.langs)

    def search(self, dense: list[float], sparse: SparseVec | None = None) -> list[Candidate]:
        c = self.cfg
        params = m.SearchParams(hnsw_ef=c.hnsw_ef,
                                quantization=m.QuantizationSearchParams(rescore=c.rescore, oversampling=c.oversampling))
        branches = [m.Prefetch(query=dense, using=DENSE, limit=c.k_dense, filter=self.filter, params=params)]
        if sparse is not None and sparse.indices:
            branches.append(m.Prefetch(query=m.SparseVector(indices=list(sparse.indices), values=list(sparse.values)),
                                       using=SPARSE, limit=c.k_sparse, filter=self.filter))
        res = self.client.query_points(self.collection, prefetch=branches, query=m.FusionQuery(fusion=m.Fusion.RRF),
                                       limit=c.k_fuse, with_payload=self.fields)
        return [hit_to_candidate(h) for h in res.points]