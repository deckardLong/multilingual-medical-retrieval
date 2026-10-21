from types import SimpleNamespace
import pytest
from retrieval.select import pick_docs


def cfg(max_docs=10, min_score=None, rel_drop=None):
    return SimpleNamespace(max_docs=max_docs, min_score=min_score, rel_drop=rel_drop)


R = [("a", 1.0), ("b", 0.5), ("c", 0.25), ("d", 0.1)]


def test_empty_ranking():
    assert pick_docs([], cfg()) == []


def test_without_thresholds_only_max_docs_applies():
    assert pick_docs(R, cfg(max_docs=3)) == ["a", "b", "c"]
    assert pick_docs(R, cfg(max_docs=99)) == ["a", "b", "c", "d"]


def test_max_docs_one_keeps_only_the_top():
    assert pick_docs(R, cfg(max_docs=1)) == ["a"]


def test_top_doc_is_kept_even_below_every_threshold():
    assert pick_docs([("a", 0.05), ("b", 0.04)], cfg(min_score=0.5, rel_drop=0.9)) == ["a"]


def test_min_score_is_inclusive():
    assert pick_docs(R, cfg(min_score=0.5)) == ["a", "b"]                   # 0.5 đúng ngưỡng: giữ
    assert pick_docs(R, cfg(min_score=0.51)) == ["a"]


def test_rel_drop_is_inclusive():
    assert pick_docs(R, cfg(rel_drop=0.5)) == ["a", "b"]                    # 0.5 = 0.5 × 1.0: giữ
    assert pick_docs(R, cfg(rel_drop=0.51)) == ["a"]


def test_rel_drop_is_relative_to_the_top_score():
    assert pick_docs([("a", 0.4), ("b", 0.2), ("c", 0.19)], cfg(rel_drop=0.5)) == ["a", "b"]


def test_strictest_threshold_wins():
    assert pick_docs(R, cfg(min_score=0.2, rel_drop=0.6)) == ["a"]         # rel_drop loại b dù b đạt min_score
    assert pick_docs(R, cfg(min_score=0.6, rel_drop=0.1)) == ["a"]         # min_score loại b dù b đạt rel_drop


def test_stops_at_the_first_failing_doc():
    assert pick_docs([("a", 1.0), ("b", 0.1), ("c", 0.9)], cfg(min_score=0.5)) == ["a"]


def test_zero_top_score_keeps_everything_up_to_max_docs():
    assert pick_docs([("a", 0.0), ("b", 0.0)], cfg(rel_drop=0.5)) == ["a", "b"]


def test_order_is_preserved():
    assert pick_docs([("z", 0.9), ("m", 0.8), ("a", 0.7)], cfg()) == ["z", "m", "a"]


@pytest.mark.parametrize("kw", [dict(min_score=0.5), dict(rel_drop=0.5)])
def test_stops_at_the_first_failing_doc_for_either_threshold(kw):
    # xếp hạng đúng ra luôn giảm dần; nếu vi phạm thì dừng ở doc đầu tiên không đạt, không "nhặt" doc phía sau
    assert pick_docs([("a", 1.0), ("b", 0.1), ("c", 0.9)], cfg(**kw)) == ["a"]