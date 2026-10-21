"""Tính chất của bước chọn doc/chunk (Hypothesis). Quan trọng cho việc chỉnh ngưỡng F2: nới/siết ngưỡng phải có hệ quả đơn điệu."""
from hypothesis import given, settings as hyp, strategies as st
from common.schema import Candidate
from retrieval.select import select
from retrieval.select.spans import _overlap_ratio
from retrieval.settings.retrieve import SelectCfg


@st.composite
def pools(draw, unique_scores=False):
    n = draw(st.integers(0, 14))
    scores = (draw(st.lists(st.floats(0.0, 1.0, allow_nan=False), min_size=n, max_size=n, unique=True))
              if unique_scores else [draw(st.floats(0.0, 1.0, allow_nan=False)) for _ in range(n)])
    out = []
    for i, score in enumerate(scores):
        k, lang = draw(st.integers(1, 5)), draw(st.sampled_from(["vi", "zh"]))          # vi:k và zh:k cùng doc_id k
        start, length = draw(st.integers(0, 200)), draw(st.integers(1, 120))
        out.append(Candidate(chunk_id=f"{lang}:{k}#{i}", uid=f"{lang}:{k}", doc_id=str(k), start=start, end=start + length,
                             p_start=start, p_end=start + length, score=score, text="t"))
    return out


@st.composite
def cfgs(draw):
    return SelectCfg(max_docs=draw(st.integers(1, 6)), chunks_per_doc=draw(st.integers(1, 4)),
                     min_score=draw(st.one_of(st.none(), st.floats(0.0, 1.0, allow_nan=False))),
                     rel_drop=draw(st.one_of(st.none(), st.floats(0.01, 1.0, allow_nan=False))))


def uids(sel):
    return list(dict.fromkeys(c.uid for c in sel.chunks))


@hyp(max_examples=300, deadline=None)
@given(cs=pools(), cfg=cfgs())
def test_selection_invariants(cs, cfg):
    sel = select(cs, cfg)
    by_id = {c.chunk_id: c for c in cs}
    assert all(c.chunk_id in by_id and by_id[c.chunk_id] == c for c in sel.chunks)          # chỉ chọn trong pool, không sửa
    assert len(uids(sel)) <= cfg.max_docs
    assert len({c.chunk_id for c in sel.chunks}) == len(sel.chunks) and len(set(sel.doc_ids)) == len(sel.doc_ids)
    assert set(sel.doc_ids) == {c.doc_id for c in sel.chunks}
    for u in uids(sel):
        mine = [c for c in sel.chunks if c.uid == u]
        assert len(mine) <= cfg.chunks_per_doc
        assert all(_overlap_ratio(a, b) <= 0.5 for i, a in enumerate(mine) for b in mine[i + 1:])
        best = max((c for c in cs if c.uid == u), key=lambda c: c.score)                      # chunk tốt nhất của doc luôn có mặt
        assert best in mine
    flat = [c.uid for c in sel.chunks]
    assert flat == sorted(flat, key=uids(sel).index)                                          # chunk cùng doc nằm liền nhau
    best_per_doc = [max(c.score for c in sel.chunks if c.uid == u) for u in uids(sel)]
    assert best_per_doc == sorted(best_per_doc, reverse=True)                                 # doc xếp theo điểm giảm dần


@hyp(max_examples=300, deadline=None)
@given(cs=pools(), cfg=cfgs())
def test_non_empty_pool_always_returns_its_top_scoring_chunk(cs, cfg):
    sel = select(cs, cfg)
    if not cs:
        assert sel.doc_ids == [] and sel.chunks == []
    else:
        assert max(c.score for c in sel.chunks) == max(c.score for c in cs)                   # doc đầu giữ bất kể ngưỡng


@hyp(max_examples=300, deadline=None)
@given(cs=pools(), cfg=cfgs(), more=st.integers(1, 5))
def test_raising_max_docs_only_appends_docs(cs, cfg, more):
    small = uids(select(cs, cfg))
    big = uids(select(cs, cfg.model_copy(update=dict(max_docs=cfg.max_docs + more))))
    assert big[:len(small)] == small


@hyp(max_examples=300, deadline=None)
@given(cs=pools(), cfg=cfgs(), lo=st.floats(0.0, 1.0, allow_nan=False), hi=st.floats(0.0, 1.0, allow_nan=False))
def test_raising_min_score_never_adds_docs(cs, cfg, lo, hi):
    lo, hi = min(lo, hi), max(lo, hi)
    loose = uids(select(cs, cfg.model_copy(update=dict(min_score=lo))))
    strict = uids(select(cs, cfg.model_copy(update=dict(min_score=hi))))
    assert strict == loose[:len(strict)]


@hyp(max_examples=300, deadline=None)
@given(cs=pools(), cfg=cfgs(), lo=st.floats(0.01, 1.0, allow_nan=False), hi=st.floats(0.01, 1.0, allow_nan=False))
def test_raising_rel_drop_never_adds_docs(cs, cfg, lo, hi):
    lo, hi = min(lo, hi), max(lo, hi)
    loose = uids(select(cs, cfg.model_copy(update=dict(rel_drop=lo))))
    strict = uids(select(cs, cfg.model_copy(update=dict(rel_drop=hi))))
    assert strict == loose[:len(strict)]


@hyp(max_examples=300, deadline=None)
@given(cs=pools(unique_scores=True), cfg=cfgs(), seed=st.randoms(use_true_random=False))
def test_input_order_does_not_matter_when_scores_are_distinct(cs, cfg, seed):
    shuffled = list(cs); seed.shuffle(shuffled)
    assert select(shuffled, cfg).chunks == select(cs, cfg).chunks


@hyp(max_examples=300, deadline=None)
@given(cs=pools(), cfg=cfgs())
def test_reselecting_a_selection_changes_nothing(cs, cfg):
    first = select(cs, cfg)
    assert select(first.chunks, cfg).chunks == first.chunks


@hyp(max_examples=200, deadline=None)
@given(cs=pools(), cfg=cfgs())
def test_input_is_never_modified(cs, cfg):
    before = [c.model_dump() for c in cs]
    select(cs, cfg)
    assert [c.model_dump() for c in cs] == before