import dataclasses
from types import SimpleNamespace
import pytest
from retrieval.search.decompose import Decomposed, build_decomposer
from retrieval.search.decompose.identity import IdentityDecomposer
from retrieval.search.decompose.rule import RuleDecomposer

MULTI = "Nguyên nhân gây bệnh tiểu đường là gì? Cách điều trị ra sao?"


@pytest.fixture
def dcfg(settings):
    return settings.retrieve.decompose


def test_rule_decompose_multi_intent(dcfg):
    d = build_decomposer(dcfg).decompose(MULTI)
    assert len(d.subs) == 2 and d.queries[0] == d.original and d.rerank_queries[0] == d.original
    assert d.queries == [d.original, *d.subs]
    assert d.subs == ["Nguyên nhân gây bệnh tiểu đường là gì", "Cách điều trị ra sao"]


def test_decomposition_is_deterministic(dcfg):
    dec = build_decomposer(dcfg)
    assert dec.decompose(MULTI) == dec.decompose(MULTI)


def test_single_intent_not_decomposed(dcfg):
    d = build_decomposer(dcfg).decompose("Triệu chứng của bệnh tiểu đường type 2?")
    assert d.subs == [] and d.queries == [d.original]


@pytest.mark.parametrize("query", ["", "   ", "?", "\n"])
def test_empty_or_punctuation_only_query_does_not_crash(dcfg, query):
    d = build_decomposer(dcfg).decompose(query)
    assert d.queries == [query] and d.subs == []


def test_keep_original_false_drops_original_from_search_only(dcfg):
    c = dcfg.model_copy(update=dict(keep_original=False))
    d = build_decomposer(c).decompose(MULTI)
    assert d.original not in d.queries and d.queries == d.subs and d.rerank_queries[0] == d.original


def test_keep_original_false_but_nothing_to_split_still_searches_the_original(dcfg):
    d = build_decomposer(dcfg.model_copy(update=dict(keep_original=False))).decompose("triệu chứng bệnh tiểu đường?")
    assert d.queries == ["triệu chứng bệnh tiểu đường?"]               # không bao giờ để danh sách tìm kiếm rỗng


def test_max_subqueries_cap_and_dedupe(dcfg):
    c = dcfg.model_copy(update=dict(max_subqueries=2))
    d = build_decomposer(c).decompose("một hai ba bốn? năm sáu bảy tám? chín mười mười một? một hai ba bốn?")
    assert len(d.subs) == 2


def test_max_subqueries_one(dcfg):
    d = build_decomposer(dcfg.model_copy(update=dict(max_subqueries=1))).decompose(MULTI)
    assert d.subs == ["Nguyên nhân gây bệnh tiểu đường là gì"]            # giữ vế đầu


def test_duplicate_parts_are_removed_ignoring_case_and_spacing(dcfg):
    d = build_decomposer(dcfg).decompose("Cách điều trị ra sao? cách  điều trị  ra sao? Nguyên nhân gây bệnh là gì?")
    assert d.subs == ["Cách điều trị ra sao", "Nguyên nhân gây bệnh là gì"]


def test_fragments_of_one_word_are_not_used_as_subqueries(dcfg):
    d = build_decomposer(dcfg).decompose("bệnh? điều trị bệnh tiểu đường?")
    assert d.subs == ["điều trị bệnh tiểu đường"]


def test_chinese_multi_intent(dcfg):
    d = build_decomposer(dcfg).decompose("糖尿病的症状是什么？如何治疗糖尿病？")
    assert d.subs == ["糖尿病的症状是什么", "如何治疗糖尿病"]


def test_conjunction_between_long_clauses_is_split(dcfg):
    d = build_decomposer(dcfg).decompose("Nguyên nhân gây bệnh tiểu đường và cách phòng ngừa hiệu quả")
    assert d.subs == ["Nguyên nhân gây bệnh tiểu đường", "cách phòng ngừa hiệu quả"]


def test_short_conjunction_is_not_split(dcfg):
    d = build_decomposer(dcfg).decompose("viêm gan B và C ảnh hưởng gan thế nào")
    assert d.subs == []


def test_min_part_tokens_controls_conjunction_splitting(dcfg):
    q = "triệu chứng bệnh và cách điều trị"                                   # vế 1 có 3 đơn vị
    assert build_decomposer(dcfg.model_copy(update=dict(min_part_tokens=4))).decompose(q).subs == []
    assert len(build_decomposer(dcfg.model_copy(update=dict(min_part_tokens=3))).decompose(q).subs) == 2


def test_decomposed_is_immutable():
    d = Decomposed("q", ["q"], [])
    with pytest.raises(dataclasses.FrozenInstanceError):
        d.original = "x"                                                    # type: ignore[misc]


def test_rerank_queries_put_original_first_without_duplicating_it():
    d = Decomposed("gốc", ["a", "b"], ["a", "b"])
    assert d.rerank_queries == ["gốc", "a", "b"]


def test_off_mode(dcfg):
    d = build_decomposer(dcfg.model_copy(update=dict(mode="off"))).decompose("a b c d? e f g h?")
    assert d.queries == ["a b c d? e f g h?"] and d.subs == []


def test_identity_decomposer_rerank_queries():
    assert IdentityDecomposer().decompose("q").rerank_queries == ["q"]


def test_build_picks_the_decomposer_by_mode(dcfg):
    assert isinstance(build_decomposer(dcfg.model_copy(update=dict(mode="off"))), IdentityDecomposer)
    assert isinstance(build_decomposer(dcfg.model_copy(update=dict(mode="rule"))), RuleDecomposer)


def test_unknown_mode_is_rejected():
    with pytest.raises(ValueError, match="llm"):
        build_decomposer(SimpleNamespace(mode="llm"))