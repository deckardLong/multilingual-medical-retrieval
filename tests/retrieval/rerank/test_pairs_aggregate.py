import pytest
from common.schema import Candidate
from retrieval.rerank.pairs import build_pairs, passage_of
from retrieval.rerank.aggregate import max_over_queries
from factories import cand


def test_passage_with_and_without_ctx():
    assert passage_of(cand(0, "nội dung", ctx="Bài | Mục")) == "Bài | Mục\nnội dung"
    assert passage_of(cand(0, "nội dung")) == "nội dung"
    assert passage_of(cand(0, "nội dung", ctx="")) == "nội dung"


def test_passage_when_text_is_missing():
    c = Candidate(chunk_id="vi:1#0", uid="vi:1", doc_id="1", start=0, end=1, p_start=0, p_end=1, score=0.5)
    assert passage_of(c) == ""                                  # text=None không được làm hỏng việc ghép


def test_pairs_order_query_major():
    cs = [cand(0, "a"), cand(1, "b")]
    assert build_pairs(["q1", "q2"], cs) == [("q1", "a"), ("q1", "b"), ("q2", "a"), ("q2", "b")]


def test_pair_index_formula_matches_aggregate_layout():
    qs, cs = ["q0", "q1", "q2"], [cand(i, f"p{i}") for i in range(4)]
    pairs = build_pairs(qs, cs)
    assert len(pairs) == len(qs) * len(cs)
    for qi in range(3):
        for ci in range(4):
            assert pairs[qi * 4 + ci] == (f"q{qi}", f"p{ci}")


def test_pairs_use_ctx_and_keep_unicode():
    out = build_pairs(["肾结石症状"], [cand(0, "内容", ctx="标题 | 小节")])
    assert out == [("肾结石症状", "标题 | 小节\n内容")]


def test_pairs_empty_inputs():
    assert build_pairs([], [cand(0, "a")]) == [] and build_pairs(["q"], []) == []


def test_max_over_queries():
    assert max_over_queries([0.1, 0.9, 0.7, 0.2], 2, 2) == [0.7, 0.9]


def test_single_query_is_identity():
    assert max_over_queries([0.3, 0.8, 0.1], 1, 3) == [0.3, 0.8, 0.1]


def test_each_chunk_takes_its_best_query():
    # 3 truy vấn × 2 chunk: chunk 0 tốt nhất ở truy vấn 2, chunk 1 ở truy vấn 0
    assert max_over_queries([0.1, 0.9,   0.2, 0.3,   0.8, 0.4], 3, 2) == [0.8, 0.9]


def test_equal_scores_are_fine():
    assert max_over_queries([0.5, 0.5, 0.5, 0.5], 2, 2) == [0.5, 0.5]


def test_no_candidates_gives_empty():
    assert max_over_queries([], 2, 0) == []


def test_max_over_queries_length_mismatch():
    with pytest.raises(ValueError):
        max_over_queries([0.1], 2, 2)
    with pytest.raises(ValueError):
        max_over_queries([0.1] * 5, 2, 2)


def test_zero_queries_with_candidates_is_an_error():
    with pytest.raises(ValueError):
        max_over_queries([], 0, 3)