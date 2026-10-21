"""Kiểm tra tính chất bằng Hypothesis: bộ tách ý không được sập, bịa chữ hay trả danh sách tìm kiếm rỗng với BẤT KỲ văn bản nào."""
from hypothesis import given, settings as hyp, strategies as st
from retrieval.search.decompose import build_decomposer
from retrieval.search.decompose.rule import _norm
from retrieval.search.decompose.splitters import count_units, split_conjunction, split_questions
from retrieval.settings.retrieve import DecomposeCfg

SEPARATORS = ["? ", "?\n", "; ", "。", "？", "\n", " và ", " and ", " cũng như ", "以及", ", "]
PHRASES = ["triệu chứng bệnh tiểu đường", "cách điều trị", "nguyên nhân gây bệnh", "糖尿病的症状", "how is it treated", "viêm gan B", "a b"]


@st.composite
def queries(draw):
    if draw(st.booleans()):
        return draw(st.text(max_size=200))                                  # văn bản bất kỳ, kể cả rác/ký tự lạ
    parts = draw(st.lists(st.sampled_from(PHRASES), min_size=0, max_size=6))
    out = ""
    for p in parts:
        out += p + draw(st.sampled_from(SEPARATORS))
    return out


@st.composite
def cfgs(draw):
    return DecomposeCfg(mode="rule", max_subqueries=draw(st.integers(1, 6)), keep_original=draw(st.booleans()),
                        min_part_tokens=draw(st.integers(1, 6)))


@hyp(max_examples=300, deadline=None)
@given(q=st.deferred(lambda: queries()), cfg=st.deferred(lambda: cfgs()))
def test_decomposition_invariants(q, cfg):
    d = build_decomposer(cfg).decompose(q)
    assert d.original == q and d.queries                                      # danh sách tìm kiếm không bao giờ rỗng
    assert d == build_decomposer(cfg).decompose(q)                            # xác định
    assert d.rerank_queries == [q, *d.subs]                                   # truy vấn gốc luôn đứng đầu khi rerank
    assert len(d.subs) <= cfg.max_subqueries
    assert d.queries == ([q, *d.subs] if cfg.keep_original else d.subs) if d.subs else d.queries == [q]
    norms = [_norm(s) for s in d.subs]
    assert len(set(norms)) == len(norms) and _norm(q) not in norms            # không trùng nhau, không trùng truy vấn gốc
    for s in d.subs:
        assert s and s == s.strip() and count_units(s) >= 2
        assert s in q                                                         # chỉ là mảnh nguyên văn của truy vấn, không bịa chữ


@hyp(max_examples=200, deadline=None)
@given(q=st.text(max_size=200))
def test_mode_off_is_always_the_identity(q):
    d = build_decomposer(DecomposeCfg(mode="off", max_subqueries=3, keep_original=True, min_part_tokens=4)).decompose(q)
    assert d.queries == [q] and d.subs == []


@hyp(max_examples=200, deadline=None)
@given(q=st.text(max_size=200))
def test_split_questions_pieces_are_clean(q):
    for piece in split_questions(q):
        assert piece and piece == piece.strip(" ,.:-–•\t")
        assert not any(ch in piece for ch in "?？;；。\n")


@hyp(max_examples=200, deadline=None)
@given(s=st.text(max_size=120), n=st.integers(1, 6))
def test_split_conjunction_is_all_or_nothing(s, n):
    parts = split_conjunction(s, n)
    assert parts, "không bao giờ trả danh sách rỗng"
    assert parts == [s] or (len(parts) >= 2 and all(count_units(p) >= n for p in parts))


@hyp(max_examples=200, deadline=None)
@given(a=st.text(alphabet="abc xyz", max_size=30), b=st.text(alphabet="abc xyz", max_size=30))
def test_count_units_is_additive_across_a_space(a, b):
    assert count_units(a + " " + b) == count_units(a) + count_units(b)