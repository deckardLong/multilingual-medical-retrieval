import pytest
from common.schema import SparseVec
from retrieval.embedding import Encoded
from retrieval.search import Retriever
from retrieval.search import retriever as retriever_module

MULTI = "Nguyên nhân gây bệnh tiểu đường là gì? Cách điều trị ra sao?"


class SpyEmbedder:
    def __init__(self, inner):
        self.inner, self.calls = inner, []

    def encode_queries(self, texts):
        self.calls.append(list(texts))
        return self.inner.encode_queries(texts)


class SpyReranker:
    def __init__(self, inner):
        self.inner, self.calls = inner, []

    def rerank(self, queries, cands):
        self.calls.append((list(queries), len(cands)))
        return self.inner.rerank(queries, cands)


def _top_docs(pool, n=2):
    seen = []
    for c in pool:
        if c.doc_id not in seen:
            seen.append(c.doc_id)
    return seen[:n]


def _r(world, decompose=None, **search_over):
    s, client, emb, rr = world
    rc = s.retrieve
    if decompose:
        rc = rc.model_copy(update=dict(decompose=rc.decompose.model_copy(update=decompose)))
    if search_over:
        rc = rc.model_copy(update=dict(search=rc.search.model_copy(update=search_over)))
    s.retrieve = rc
    return Retriever(s, client, emb, rr)


def _spy_search(r):
    calls, orig = [], r.searcher.search
    def spy(vectors):
        calls.append(len(vectors))
        return orig(vectors)
    r.searcher.search = spy
    return calls


# ---- chỉ rerank phần đầu pool -----------------------------------------------------------------------------------

def test_only_top_n_is_reranked_and_the_tail_follows_below_it(world):
    s, client, emb, rr = world
    s.rerank = s.rerank.model_copy(update=dict(top_n=2))
    spy = SpyReranker(rr)
    r = Retriever(s, client, emb, spy)
    fused = r.searcher.search([(emb.encode_queries(["bệnh"]).dense[0].tolist(), None)])
    assert len(fused) > 2
    (pool,), _ = r.pools(["bệnh"])
    assert [n for _, n in spy.calls] == [2]
    head, tail = pool[:2], pool[2:]
    assert {c.chunk_id for c in tail} == {c.chunk_id for c in fused[2:]}            # đuôi giữ nguyên thứ tự hybrid
    assert [c.chunk_id for c in tail] == [c.chunk_id for c in fused if c.chunk_id in {t.chunk_id for t in tail}]
    assert min(c.score for c in head) >= max(c.score for c in tail)
    assert [c.score for c in pool] == sorted((c.score for c in pool), reverse=True)


def test_top_n_none_reranks_the_whole_pool(world):
    s, client, emb, rr = world
    s.rerank = s.rerank.model_copy(update=dict(top_n=None))
    spy = SpyReranker(rr)
    (pool,), _ = Retriever(s, client, emb, spy).pools(["bệnh"])
    assert [n for _, n in spy.calls] == [len(pool)]


# ---- kết quả tìm kiếm -------------------------------------------------------------------------------------------

def test_finds_the_right_doc(world):
    pools, errs = _r(world).pools(["triệu chứng của bệnh tiểu đường"])
    assert not errs and _top_docs(pools[0])[0] == "1"
    assert all(c.text and c.ctx and c.doc_id for c in pools[0])             # đủ payload cho reranker và C2
    assert [c.score for c in pools[0]] == sorted([c.score for c in pools[0]], reverse=True)


def test_scores_are_rerank_scores_in_unit_range(world):
    pools, _ = _r(world).pools(["triệu chứng của bệnh tiểu đường"])
    assert pools[0] and all(0.0 <= c.score <= 1.0 for c in pools[0])


def test_multi_intent_query_reaches_both_docs(world):
    q = "Cao huyết áp gây đau đầu và chóng mặt không? Thuốc giãn phế quản dùng cho người hen suyễn?"
    pools, _ = _r(world).pools([q])
    assert {"2", "3"} <= set(_top_docs(pools[0], 3))


def test_lang_filter(world):
    pools, _ = _r(world, langs=["zh"]).pools(["triệu chứng của bệnh tiểu đường"])
    assert pools[0] and {c.uid for c in pools[0]} == {"zh:4"}
    pools, _ = _r(world, langs=["vi"]).pools(["糖尿病的症状"])
    assert all(c.uid.startswith("vi:") for c in pools[0])


def test_k_pool_caps_pool(world):
    pools, _ = _r(world, k_pool=2, k_fuse=2).pools(["bệnh"])
    assert len(pools[0]) <= 2


def test_pools_keep_input_order_and_length(world):
    pools, errs = _r(world).pools(["bệnh tiểu đường", "cao huyết áp", "hen suyễn"])
    assert not errs and [_top_docs(p)[0] for p in pools] == ["1", "2", "3"]


def test_empty_batch(world):
    assert _r(world).pools([]) == ([], {})


def test_progress_bar_advances_once_per_query(world):
    class Bar:
        total = 0
        def __init__(self, desc, total, unit="it"): Bar.total = total
        def __enter__(self): return self
        def __exit__(self, *exc): return False
        def advance(self, n=1): Bar.advanced = getattr(Bar, "advanced", 0) + n
        def where(self, label): Bar.label = label

    _r(world).pools(["bệnh tiểu đường", "cao huyết áp", "hen suyễn"], Bar)
    assert (Bar.total, Bar.advanced) == (3, 3) and "rerank" in Bar.label


def test_empty_collection_gives_empty_pool(world):
    s, client, emb, rr = world
    from retrieval.index import ensure_collection
    ensure_collection(client, "blank", s.index, s.embed)
    pools, errs = Retriever(s, client, emb, rr, collection="blank").pools(["bất kỳ"])
    assert pools == [[]] and not errs


# ---- tách ý và số lần tìm ---------------------------------------------------------------------------------------

def test_each_query_makes_one_search_call_with_original_plus_subqueries(world):
    r = _r(world)
    calls = _spy_search(r)
    r.pools([MULTI, "bệnh tiểu đường"])
    assert calls == [3, 1]                                  # gốc + 2 truy vấn con; truy vấn đơn ý chỉ có gốc


def test_decompose_off_searches_only_the_original(world):
    r = _r(world, decompose=dict(mode="off"))
    calls = _spy_search(r)
    r.pools([MULTI])
    assert calls == [1]


def test_keep_original_false_searches_only_the_subqueries(world):
    r = _r(world, decompose=dict(keep_original=False))
    calls = _spy_search(r)
    r.pools([MULTI])
    assert calls == [2]


def test_reranker_gets_original_first_then_subqueries(world):
    s, client, emb, rr = world
    spy = SpyReranker(rr)
    _r(world)
    Retriever(s, client, emb, spy).pools([MULTI])
    queries, n = spy.calls[0]
    assert queries == [MULTI, "Nguyên nhân gây bệnh tiểu đường là gì", "Cách điều trị ra sao"] and n > 0


def test_reranker_gets_only_the_original_when_decompose_is_off(world):
    s, client, emb, rr = world
    spy = SpyReranker(rr)
    _r(world, decompose=dict(mode="off"))
    Retriever(s, client, emb, spy).pools([MULTI])
    assert spy.calls[0][0] == [MULTI]


def test_reranker_still_gets_original_first_when_keep_original_is_false(world):
    s, client, emb, rr = world
    spy = SpyReranker(rr)
    _r(world, decompose=dict(keep_original=False))
    Retriever(s, client, emb, spy).pools([MULTI])
    assert spy.calls[0][0][0] == MULTI                                       # gốc vẫn đứng đầu dù không dùng để tìm


def test_pool_is_exactly_the_rerankers_output(world):
    s, client, emb, _ = world
    class Reverse:
        def rerank(self, queries, cands): return list(reversed(cands))
    r = Retriever(s, client, emb, Reverse())
    merged = []
    orig = r.searcher.search
    r.searcher.search = lambda vectors: (merged.append(orig(vectors)), merged[-1])[1]
    pools, _ = r.pools(["bệnh tiểu đường"])
    assert pools[0] == list(reversed(merged[0]))


# ---- mã hoá truy vấn --------------------------------------------------------------------------------------------

def test_each_distinct_text_is_embedded_once_across_the_batch(world):
    s, client, emb, rr = world
    spy = SpyEmbedder(emb)
    s.retrieve = s.retrieve.model_copy(update=dict(decompose=s.retrieve.decompose.model_copy(update=dict(mode="off"))))
    Retriever(s, client, spy, rr).pools(["bệnh tiểu đường", "bệnh tiểu đường", "cao huyết áp"])
    texts = [t for call in spy.calls for t in call]
    assert sorted(texts) == ["bệnh tiểu đường", "cao huyết áp"]


def test_subquery_shared_by_two_queries_is_embedded_once(world):
    s, client, emb, rr = world
    spy = SpyEmbedder(emb)
    q2 = "Cách điều trị ra sao? Triệu chứng của bệnh là gì?"
    Retriever(s, client, spy, rr).pools([MULTI, q2])
    texts = [t for call in spy.calls for t in call]
    assert len(texts) == len(set(texts)) and "Cách điều trị ra sao" in texts


def test_encoding_is_done_in_slices(world, monkeypatch):
    s, client, emb, rr = world
    spy = SpyEmbedder(emb)
    monkeypatch.setattr(retriever_module, "ENCODE_SLICE", 2)
    s.retrieve = s.retrieve.model_copy(update=dict(decompose=s.retrieve.decompose.model_copy(update=dict(mode="off"))))
    qs = ["bệnh tiểu đường", "cao huyết áp", "hen suyễn", "khó thở", "đau đầu"]
    pools, errs = Retriever(s, client, spy, rr).pools(qs)
    assert [len(c) for c in spy.calls] == [2, 2, 1] and len(pools) == 5 and not errs


def test_dense_only_embedder_output_still_works(world):
    s, client, emb, rr = world
    class DenseOnly:
        def encode_queries(self, texts):
            return Encoded(emb.encode_queries(texts).dense, [])                  # không có sparse
    pools, errs = Retriever(s, client, DenseOnly(), rr).pools(["bệnh tiểu đường"])
    assert not errs and pools[0]


def test_embedder_failure_aborts_the_whole_batch(world):
    s, client, _, rr = world
    class Boom:
        def encode_queries(self, texts): raise RuntimeError("hết VRAM")
    with pytest.raises(RuntimeError, match="hết VRAM"):                       # lỗi hệ thống, không phải lỗi từng truy vấn
        Retriever(s, client, Boom(), rr).pools(["bệnh tiểu đường"])


# ---- cách ly lỗi ------------------------------------------------------------------------------------------------

def test_batch_keeps_order_and_isolates_failures(world):
    s, client, emb, rr = world
    r = Retriever(s, client, emb, rr)
    orig = r.searcher.search
    flaky_n = [0]
    def flaky(vectors):
        if flaky_n[0] == 1:
            flaky_n[0] += 1; raise RuntimeError("qdrant sập")
        flaky_n[0] += 1; return orig(vectors)
    r.searcher.search = flaky
    pools, errs = r.pools(["bệnh tiểu đường", "cao huyết áp", "hen suyễn"])
    assert list(errs) == [1] and "qdrant sập" in errs[1] and pools[1] == [] and pools[0] and pools[2]


def test_error_text_names_the_exception_type(world):
    r = _r(world)
    def fail_search(vectors):
        raise ConnectionError("không nối được")
    r.searcher.search = fail_search
    _, errs = r.pools(["bệnh"])
    assert errs == {0: "ConnectionError: không nối được"}


def test_reranker_failure_is_isolated_too(world):
    s, client, emb, rr = world
    class Flaky:
        n = 0
        def rerank(self, queries, cands):
            Flaky.n += 1
            if Flaky.n == 2:
                raise ValueError("điểm hỏng")
            return rr.rerank(queries, cands)
    pools, errs = Retriever(s, client, emb, Flaky()).pools(["bệnh tiểu đường", "cao huyết áp", "hen suyễn"])
    assert list(errs) == [1] and errs[1].startswith("ValueError") and pools[1] == [] and pools[0] and pools[2]


def test_unknown_collection_is_reported_per_query_not_raised(world):
    s, client, emb, rr = world
    pools, errs = Retriever(s, client, emb, rr, collection="không-có-collection").pools(["a", "b"])
    assert pools == [[], []] and sorted(errs) == [0, 1]


# ---- vector đúng truy vấn, và offset còn nguyên đầu-cuối --------------------------------------------------------

def test_each_search_query_gets_its_own_vector_in_order(world):
    s, client, emb, rr = world
    r = _r(world)
    captured, orig = [], r.searcher.search
    r.searcher.search = lambda vectors: (captured.append(vectors), orig(vectors))[1]
    r.pools([MULTI])
    (vectors,) = captured
    expected = [MULTI, "Nguyên nhân gây bệnh tiểu đường là gì", "Cách điều trị ra sao"]
    assert len(vectors) == 3
    for (dense, sparse), q in zip(vectors, expected):
        e = emb.encode_queries([q])
        assert dense == e.dense[0].tolist() and sparse == e.sparse[0]


def test_candidates_text_and_offsets_match_the_original_documents(world, docs):
    """Chunk → embed → Qdrant → truy hồi: text trả về phải đúng bằng văn bản gốc cắt theo (start, end)."""
    pools, _ = _r(world).pools(["triệu chứng của bệnh tiểu đường", "cao huyết áp", "hen suyễn khó thở"])
    seen = 0
    for pool in pools:
        for c in pool:
            doc = docs[c.uid]
            assert doc.text[c.start:c.end] == c.text
            assert c.p_start <= c.start and c.end <= c.p_end and c.p_end <= len(doc.text)
            assert c.text in doc.text[c.p_start:c.p_end] and c.doc_id == doc.doc_id
            seen += 1
    assert seen > 0