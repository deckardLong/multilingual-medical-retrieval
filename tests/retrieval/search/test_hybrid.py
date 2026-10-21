"""HybridSearcher: (1) kiểm tra YÊU CẦU gửi cho Qdrant bằng client giả; (2) kiểm tra KẾT QUẢ trên Qdrant trong bộ nhớ."""
from types import SimpleNamespace
import pytest
from qdrant_client import models as m
from common.schema import SparseVec
from retrieval.index import DENSE, SPARSE
from retrieval.search import HybridSearcher
from retrieval.search.filters import lang_filter

FIELDS = ["chunk_id", "uid", "doc_id", "start", "end", "p_start", "p_end", "text", "ctx"]


class CapturingClient:
    def __init__(self, points=()):
        self.calls, self.points = [], list(points)

    def query_points(self, collection, **kw):
        self.calls.append(dict(collection=collection, **kw))
        return SimpleNamespace(points=self.points)


def hit(i, score):
    return SimpleNamespace(score=score, payload=dict(chunk_id=f"vi:1#{i}", uid="vi:1", doc_id="1", start=i, end=i + 1,
                                                     p_start=i, p_end=i + 1, text="t", ctx="c"))


@pytest.fixture
def cfg(settings):
    return settings.retrieve.search.model_copy(update=dict(k_dense=11, k_sparse=12, k_fuse=7, k_pool=5, rrf_k=33,
                                                           hnsw_ef=77, rescore=True, oversampling=1.5, langs=None))


def search(cfg, vectors, points=()):
    client = CapturingClient(points)
    out = HybridSearcher(client, "col", cfg, FIELDS).search(vectors)
    return client.calls[0], out


DENSE_V = [0.1, 0.2, 0.3]
SPARSE_V = SparseVec([4, 9], [0.5, 0.25])


# ---- yêu cầu gửi cho Qdrant -------------------------------------------------------------------------------------

def test_single_call_with_global_rrf_and_pool_limit(cfg):
    client = CapturingClient()
    HybridSearcher(client, "col", cfg, FIELDS).search([(DENSE_V, SPARSE_V), (DENSE_V, SPARSE_V)])
    assert len(client.calls) == 1                                           # một lần gọi mạng cho cả truy vấn
    c = client.calls[0]
    assert c["collection"] == "col" and c["limit"] == 5 and c["with_payload"] == FIELDS
    assert c["query"] == m.RrfQuery(rrf=m.Rrf(k=33))


def test_one_nested_prefetch_per_search_query(cfg):
    call, _ = search(cfg, [(DENSE_V, SPARSE_V), ([0.9, 0.8, 0.7], SparseVec([1], [1.0])), (DENSE_V, None)])
    assert len(call["prefetch"]) == 3
    for pf in call["prefetch"]:
        assert pf.limit == 7 and pf.query == m.FusionQuery(fusion=m.Fusion.RRF)      # RRF trong từng truy vấn con


def test_dense_and_sparse_branches(cfg):
    call, _ = search(cfg, [(DENSE_V, SPARSE_V)])
    dense, sparse = call["prefetch"][0].prefetch
    assert (dense.using, dense.limit, dense.query) == (DENSE, 11, DENSE_V)
    assert (sparse.using, sparse.limit) == (SPARSE, 12)
    assert sparse.query == m.SparseVector(indices=[4, 9], values=[0.5, 0.25])


def test_dense_branch_carries_hnsw_and_quantization_params_sparse_does_not(cfg):
    call, _ = search(cfg, [(DENSE_V, SPARSE_V)])
    dense, sparse = call["prefetch"][0].prefetch
    assert dense.params.hnsw_ef == 77
    assert dense.params.quantization == m.QuantizationSearchParams(rescore=True, oversampling=1.5)
    assert sparse.params is None


@pytest.mark.parametrize("sparse", [None, SparseVec([], [])], ids=["none", "empty"])
def test_sparse_branch_omitted_when_query_has_no_sparse_terms(cfg, sparse):
    call, _ = search(cfg, [(DENSE_V, sparse)])
    (only,) = call["prefetch"][0].prefetch
    assert only.using == DENSE


def test_language_filter_applied_to_every_branch(cfg):
    call, _ = search(cfg.model_copy(update=dict(langs=["vi", "zh"])), [(DENSE_V, SPARSE_V), (DENSE_V, SPARSE_V)])
    expected = lang_filter(["vi", "zh"])
    branches = [b for pf in call["prefetch"] for b in pf.prefetch]
    assert len(branches) == 4 and all(b.filter == expected for b in branches)


def test_no_filter_when_langs_is_null(cfg):
    call, _ = search(cfg, [(DENSE_V, SPARSE_V)])
    assert all(b.filter is None for b in call["prefetch"][0].prefetch)


def test_vectors_are_copied_not_shared(cfg):
    sp = SparseVec([4, 9], [0.5, 0.25])
    call, _ = search(cfg, [(DENSE_V, sp)])
    sp.indices.append(99)                                                   # sửa dữ liệu gốc sau khi dựng yêu cầu
    assert call["prefetch"][0].prefetch[1].query.indices == [4, 9]


def test_hits_become_candidates_in_qdrant_order_with_their_scores(cfg):
    _, out = search(cfg, [(DENSE_V, SPARSE_V)], points=[hit(2, 0.9), hit(0, 0.4)])
    assert [(c.chunk_id, c.score) for c in out] == [("vi:1#2", 0.9), ("vi:1#0", 0.4)]


def test_no_hits_gives_empty_list(cfg):
    assert search(cfg, [(DENSE_V, SPARSE_V)])[1] == []


# ---- kết quả trên Qdrant thật (trong bộ nhớ) --------------------------------------------------------------------

def _vec(emb, q):
    e = emb.encode_queries([q])
    return e.dense[0].tolist(), e.sparse[0]


def test_dense_only_works_when_sparse_missing(world):
    s, client, emb, _ = world
    hs = HybridSearcher(client, s.collection, s.retrieve.search, s.index.payload_fields)
    assert hs.search([(_vec(emb, "tiểu đường")[0], None)])


def test_chunk_hit_by_several_subqueries_ranks_first(world):
    s, client, emb, _ = world
    hs = HybridSearcher(client, s.collection, s.retrieve.search, s.index.payload_fields)
    top = hs.search([_vec(emb, q) for q in ["bệnh tiểu đường triệu chứng", "tiểu đường điều trị insulin", "cao huyết áp"]])
    assert top[0].doc_id == "1"                                           # khớp 2/3 truy vấn con
    assert len({c.chunk_id for c in top}) == len(top)                       # đã khử trùng
    assert {"1", "2"} <= {c.doc_id for c in top}


def test_k_pool_limits_merged_result(world):
    s, client, emb, _ = world
    hs = HybridSearcher(client, s.collection, s.retrieve.search.model_copy(update=dict(k_pool=2)), s.index.payload_fields)
    assert len(hs.search([_vec(emb, "bệnh")])) == 2


def test_language_filter_restricts_results(world):
    s, client, emb, _ = world
    cfg = s.retrieve.search.model_copy(update=dict(langs=["zh"]))
    out = HybridSearcher(client, s.collection, cfg, s.index.payload_fields).search([_vec(emb, "tiểu đường")])
    assert out and {c.uid for c in out} == {"zh:4"}


def test_payload_fields_are_returned(world):
    s, client, emb, _ = world
    out = HybridSearcher(client, s.collection, s.retrieve.search, s.index.payload_fields).search([_vec(emb, "tiểu đường")])
    assert all(c.text and c.ctx and c.doc_id and c.end > c.start for c in out)
    assert all(c.p_start <= c.start and c.end <= c.p_end for c in out)


def test_results_are_sorted_by_fused_score(world):
    s, client, emb, _ = world
    out = HybridSearcher(client, s.collection, s.retrieve.search, s.index.payload_fields).search([_vec(emb, "bệnh tiểu đường")])
    assert [c.score for c in out] == sorted((c.score for c in out), reverse=True)