import sys, types
from types import SimpleNamespace
import pytest
from retrieval.rerank import build_pair_scorer
from retrieval.rerank.backends.fake import FakePairScorer


def test_registry_fake(rcfg):
    assert isinstance(build_pair_scorer(rcfg), FakePairScorer)


def test_registry_unknown(rcfg):
    with pytest.raises(ValueError):
        build_pair_scorer(rcfg.model_copy(update=dict(backend="x")))


def test_registry_bge_reranker_gets_model_name_and_fp16(monkeypatch, rcfg):
    mod = types.ModuleType("FlagEmbedding")
    setattr(mod, "FlagReranker", lambda name, use_fp16: SimpleNamespace(name=name, use_fp16=use_fp16))
    monkeypatch.setitem(sys.modules, "FlagEmbedding", mod)
    from retrieval.rerank.backends.bge_reranker import BgeRerankerScorer
    s = build_pair_scorer(rcfg.model_copy(update=dict(backend="bge_reranker")))
    assert isinstance(s, BgeRerankerScorer)
    assert getattr(s.m, "name") == rcfg.model and getattr(s.m, "use_fp16") is rcfg.fp16


def test_fake_backend_does_not_need_flagembedding(monkeypatch, rcfg):
    monkeypatch.setitem(sys.modules, "FlagEmbedding", None)        # import sẽ báo ImportError
    assert isinstance(build_pair_scorer(rcfg), FakePairScorer)


def test_fake_scores_overlap_in_unit_range(rcfg):
    s = build_pair_scorer(rcfg).score_pairs([("tiểu đường", "bệnh tiểu đường type 2"), ("ung thư", "tiểu đường"), ("", "x")])
    assert s[0] == 1.0 and s[1] == 0.0 and s[2] == 0.0
    assert build_pair_scorer(rcfg).score_pairs([]) == []


def test_fake_partial_overlap_is_a_fraction_of_query_words(rcfg):
    # truy vấn có 4 từ (triệu, chứng, tiểu, đường), passage chứa 2 trong số đó
    assert build_pair_scorer(rcfg).score_pairs([("triệu chứng tiểu đường", "bệnh tiểu đường")]) == [pytest.approx(0.5)]


def test_fake_is_case_insensitive_and_deterministic(rcfg):
    sc = build_pair_scorer(rcfg)
    pairs = [("Tiểu Đường", "bệnh tiểu đường"), ("tiểu đường", "BỆNH TIỂU ĐƯỜNG")]
    assert sc.score_pairs(pairs) == sc.score_pairs(pairs) == [1.0, 1.0]


def test_fake_keeps_pair_order_and_length(rcfg):
    pairs = [("a", "a"), ("a", "b"), ("b", "b"), ("c", "a b c")]
    assert build_pair_scorer(rcfg).score_pairs(pairs) == [1.0, 0.0, 1.0, 1.0]


def test_fake_handles_chinese(rcfg):
    assert build_pair_scorer(rcfg).score_pairs([("肾结石症状", "肾结石症状"), ("肾结石症状", "糖尿病")]) == [1.0, 0.0]


@pytest.mark.parametrize("q,p", [("a b c", "a"), ("a", "a b c d"), ("   ", "x"), ("x", ""), ("a a a", "a")])
def test_fake_scores_always_within_unit_range(rcfg, q, p):
    (s,) = build_pair_scorer(rcfg).score_pairs([(q, p)])
    assert 0.0 <= s <= 1.0