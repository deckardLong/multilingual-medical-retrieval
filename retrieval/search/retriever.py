import logging
import time
from typing import Callable
from common.schema import Candidate, SparseVec
from retrieval.progress import BarFactory, no_bars, quiet_tqdm
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

    def _rerank(self, queries: list[str], candidates: list[Candidate]) -> list[Candidate]:
        """Rerank top_n chunk đầu (theo thứ tự hybrid); phần đuôi nối sau với điểm thấp dần, luôn dưới mọi chunk đã rerank."""
        n = self.s.rerank.top_n
        if not n or len(candidates) <= n:
            return self.reranker.rerank(queries, candidates)
        head = self.reranker.rerank(queries, candidates[:n])
        tail = candidates[n:]
        floor = max(0.0, min((c.score for c in head), default=0.0))
        return head + [c.model_copy(update={"score": floor * (1 - (i + 1) / (len(tail) + 1))}) for i, c in enumerate(tail)]

    def pools(self, queries: list[str], make_bar: BarFactory = no_bars,
              on_done: Callable[[int, list[Candidate]], None] | None = None) -> tuple[list[list[Candidate]], dict[int, str]]:
        """Pool đã rerank cho từng truy vấn + lỗi theo chỉ số (truy vấn lỗi cho pool rỗng, không làm hỏng cả lô).
        on_done(chỉ số, pool) được gọi ngay khi một truy vấn xong thành công."""
        decs = [self.decomposer.decompose(q) for q in queries]
        texts = sorted({sq for d in decs for sq in d.queries})
        t0 = time.time()
        log.info("Tách ý: %d truy vấn → %d câu cần mã hoá, %d cặp rerank/truy vấn (tối đa)",
                 len(queries), len(texts), max((len(d.rerank_queries) for d in decs), default=0) * self.searcher.cfg.k_pool)
        with quiet_tqdm():
            vecs = self._encode(texts)
        log.info("Mã hoá xong %d câu trong %.1fs", len(texts), time.time() - t0)
        pools, errors = [], {}
        t_search = t_rerank = 0.0
        with make_bar("Truy hồi + rerank", len(decs), "q") as bar:
            for i, d in enumerate(decs):
                try:
                    t1 = time.time()
                    candidates = self.searcher.search([vecs[q] for q in d.queries])
                    t2 = time.time()
                    with quiet_tqdm():
                        pools.append(self._rerank(d.rerank_queries, candidates))
                    t_search += t2 - t1; t_rerank += time.time() - t2
                except Exception as e:                  # noqa: BLE001
                    log.error("truy vấn %d lỗi: %s", i, e)
                    pools.append([]); errors[i] = f"{type(e).__name__}: {e}"
                else:
                    if on_done is not None:
                        on_done(i, pools[-1])
                bar.where(f"tìm {t_search / (i + 1):.2f}s · rerank {t_rerank / (i + 1):.2f}s/q · lỗi {len(errors)}")
                bar.advance()
        log.info("Xong %d truy vấn: tìm kiếm %.0fs, rerank %.0fs, lỗi %d", len(decs), t_search, t_rerank, len(errors))
        return pools, errors