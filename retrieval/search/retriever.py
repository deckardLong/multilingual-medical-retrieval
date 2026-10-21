import logging
from common.schema import Candidate, SparseVec
from .decompose import build_decomposer
from .hybrid import HybridSearcher

log = logging.getLogger(__name__)
ENCODE_SLICE = 256


class Retriever:
    """truy vấn → (tách ý) → hybrid từng truy vấn con → gộp RRF → rerank → pool đã chấm điểm.
    Bước chọn doc/chunk cuối cùng nằm ở retrieval.select (tách riêng để chỉnh ngưỡng mà không chạy lại GPU)."""

    def __init__(self, settings, client, embedder, reranker, collection: str | None = None):
        self.s, self.embedder, self.reranker = settings, embedder, reranker
        rc = settings.retrieve
        self.decomposer = build_decomposer(rc.decompose)
        self.searcher = HybridSearcher(client, collection or settings.collection, rc.search, settings.index.payload_fields)

    def _encode(self, texts: list[str]) -> dict[str, tuple[list[float], SparseVec]]:
        out = {}
        for i in range(0, len(texts), ENCODE_SLICE):
            part = texts[i:i + ENCODE_SLICE]
            enc = self.embedder.encode_queries(part)
            for t, d, sp in zip(part, enc.dense, enc.sparse or [SparseVec([], [])] * len(part)):
                out[t] = (d.tolist(), sp)
        return out

    def pools(self, queries: list[str]) -> tuple[list[list[Candidate]], dict[int, str]]:
        """Pool đã rerank cho từng truy vấn + lỗi theo chỉ số (truy vấn lỗi cho pool rỗng, không làm hỏng cả lô)."""
        decs = [self.decomposer.decompose(q) for q in queries]
        vecs = self._encode(sorted({sq for d in decs for sq in d.queries}))
        pools, errors = [], {}
        for i, d in enumerate(decs):
            try:
                candidates = self.searcher.search([vecs[q] for q in d.queries])
                pools.append(self.reranker.rerank(d.rerank_queries, candidates))
            except Exception as e:                  # noqa: BLE001
                log.error("truy vấn %d lỗi: %s", i, e)
                pools.append([]); errors[i] = f"{type(e).__name__}: {e}"
        return pools, errors