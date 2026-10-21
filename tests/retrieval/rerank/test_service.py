import pytest
from retrieval.rerank import build_reranker, Reranker, NoopReranker, RerankError
from factories import cand


def pool():
    return [cand(0, "chế độ ăn cho người cao huyết áp", score=0.9),
            cand(1, "triệu chứng của bệnh tiểu đường", score=0.8),
            cand(2, "thuốc điều trị tiểu đường", score=0.7)]


class Spy:
    """Bộ chấm giả ghi lại các lần gọi; điểm lấy từ bảng {(query, passage): điểm}, mặc định 0.1."""
    def __init__(self, table=None, default=0.1):
        self.calls, self.table, self.default = [], table or {}, default

    def score_pairs(self, pairs):
        self.calls.append(list(pairs))
        return [self.table.get(p, self.default) for p in pairs]


def test_enabled_builds_real_reranker(rcfg):
    assert isinstance(build_reranker(rcfg), Reranker)


def test_sorted_by_rerank_score_and_input_untouched(rcfg):
    cs = pool(); before = [c.model_dump() for c in cs]
    out = build_reranker(rcfg).rerank(["triệu chứng tiểu đường"], cs)
    assert out[0].chunk_id == "vi:1#1" and out[0].score == pytest.approx(1.0)
    assert [c.score for c in out] == sorted([c.score for c in out], reverse=True)
    assert [c.model_dump() for c in cs] == before


def test_every_candidate_is_kept_exactly_once(rcfg):
    out = build_reranker(rcfg).rerank(["tiểu đường"], pool())
    assert sorted(c.chunk_id for c in out) == sorted(c.chunk_id for c in pool())


def test_only_score_changes_other_fields_survive(rcfg):
    cs = [cand(0, "triệu chứng tiểu đường", ctx="Bài | Mục", score=0.2)]
    (out,) = build_reranker(rcfg).rerank(["triệu chứng tiểu đường"], cs)
    assert out is not cs[0]                                      # bản sao, không phải chính đối tượng cũ
    assert {k: v for k, v in out.model_dump().items() if k != "score"} == \
           {k: v for k, v in cs[0].model_dump().items() if k != "score"}
    assert out.score != cs[0].score


def test_ties_keep_original_order(rcfg):
    cs = [cand(i, "không liên quan") for i in range(4)]
    assert [c.chunk_id for c in build_reranker(rcfg).rerank(["tiểu đường"], cs)] == [c.chunk_id for c in cs]


def test_rerank_can_overturn_retrieval_order(rcfg):
    out = build_reranker(rcfg).rerank(["thuốc điều trị tiểu đường"], pool())
    assert [c.chunk_id for c in out][0] == "vi:1#2"              # chunk 2 vốn xếp cuối theo điểm truy hồi


def test_max_over_subqueries_vs_original(rcfg):
    qs = ["bệnh gì", "thuốc điều trị tiểu đường"]          # chỉ truy vấn con khớp chunk 2
    multi = build_reranker(rcfg).rerank(qs, pool())
    orig = build_reranker(rcfg.model_copy(update=dict(query_mode="original"))).rerank(qs, pool())
    assert multi[0].chunk_id == "vi:1#2" and multi[0].score == 1.0
    assert orig[0].score < 1.0


def test_three_subqueries_each_chunk_takes_its_best(rcfg):
    cs = [cand(0, "a"), cand(1, "b"), cand(2, "c")]
    spy = Spy({("q1", "a"): 0.4, ("q2", "b"): 0.9, ("q3", "c"): 0.6, ("q3", "a"): 0.7})
    out = Reranker(spy, rcfg).rerank(["q0", "q1", "q2", "q3"], cs)
    assert [(c.chunk_id, c.score) for c in out] == [("vi:1#1", 0.9), ("vi:1#0", 0.7), ("vi:1#2", 0.6)]


def test_scorer_called_once_with_all_pairs(rcfg):
    spy = Spy()
    Reranker(spy, rcfg).rerank(["q0", "q1", "q2"], pool())
    assert len(spy.calls) == 1 and len(spy.calls[0]) == 3 * 3            # một lượt chấm, không gọi lẻ từng truy vấn


def test_original_mode_scores_only_the_first_query(rcfg):
    spy = Spy()
    Reranker(spy, rcfg.model_copy(update=dict(query_mode="original"))).rerank(["gốc", "con 1", "con 2"], pool())
    assert len(spy.calls[0]) == 3 and {q for q, _ in spy.calls[0]} == {"gốc"}


def test_empty_pool_and_no_query(rcfg):
    r = build_reranker(rcfg)
    assert r.rerank(["q"], []) == []
    with pytest.raises(ValueError, match="ít nhất một truy vấn"):
        r.rerank([], pool())


def test_empty_pool_does_not_call_the_scorer(rcfg):
    spy = Spy()
    assert Reranker(spy, rcfg).rerank(["q"], []) == [] and spy.calls == []


def test_single_candidate(rcfg):
    out = build_reranker(rcfg).rerank(["tiểu đường"], [cand(0, "tiểu đường")])
    assert len(out) == 1 and out[0].score == 1.0


def test_same_chunk_twice_is_kept_twice(rcfg):
    out = build_reranker(rcfg).rerank(["tiểu đường"], [cand(0, "tiểu đường"), cand(0, "tiểu đường")])
    assert len(out) == 2


@pytest.mark.parametrize("make", [
    lambda n: [2.0] * n,                    # quá 1
    lambda n: [-0.1] * n,                   # âm
    lambda n: [float("nan")] * n,
    lambda n: [0.5] * (n - 1),              # thiếu điểm
    lambda n: [0.5] * (n + 1),              # thừa điểm
], ids=["above_1", "negative", "nan", "too_few", "too_many"])
def test_bad_scorer_output_aborts(rcfg, make):
    class Bad:
        def score_pairs(self, pairs): return make(len(pairs))
    with pytest.raises(RerankError):
        Reranker(Bad(), rcfg).rerank(["q"], pool())


def test_scorer_exception_propagates(rcfg):
    class Boom:
        def score_pairs(self, pairs): raise RuntimeError("model sập")
    with pytest.raises(RuntimeError, match="model sập"):
        Reranker(Boom(), rcfg).rerank(["q"], pool())


def test_ctx_is_part_of_passage(rcfg):
    c = [cand(0, "nội dung chung", ctx="Tiểu đường | Triệu chứng"), cand(1, "nội dung chung")]
    out = build_reranker(rcfg).rerank(["triệu chứng tiểu đường"], c)
    assert out[0].chunk_id == "vi:1#0"


def test_disabled_returns_noop_without_loading_model(rcfg):
    r = build_reranker(rcfg.model_copy(update=dict(enabled=False, backend="bge_reranker")))
    assert isinstance(r, NoopReranker)
    assert [c.score for c in r.rerank(["q"], pool())] == [0.9, 0.8, 0.7]


def test_noop_sorts_descending_and_is_stable():
    cs = [cand(0, "a", score=0.5), cand(1, "b", score=0.9), cand(2, "c", score=0.5)]
    assert [c.chunk_id for c in NoopReranker().rerank(["q"], cs)] == ["vi:1#1", "vi:1#0", "vi:1#2"]


def test_noop_does_not_modify_its_input_and_accepts_no_query():
    cs = [cand(0, "a", score=0.1), cand(1, "b", score=0.9)]
    out = NoopReranker().rerank([], cs)
    assert [c.chunk_id for c in cs] == ["vi:1#0", "vi:1#1"] and out is not cs
    assert NoopReranker().rerank(["q"], []) == []