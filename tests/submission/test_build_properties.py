"""Tính chất của bước dựng bài nộp (Hypothesis): với MỌI kết quả truy hồi, bài nộp phải hợp lệ và không bịa nội dung."""
import tempfile
from pathlib import Path
from hypothesis import given, settings as hyp, strategies as st
from common.schema import Candidate
from retrieval.chunking.tokens import build_counter
from retrieval.results import QueryResult
from submission import SUBMISSION, build_items
from submission.checks import check_items
from submission.pack import make_zip, read_zip, write_json
from submission.settings import BuildCfg

TEXT = st.text(min_size=1, max_size=60).filter(lambda s: s.strip())


@st.composite
def results(draw):
    out = []
    for qid in draw(st.lists(st.integers(0, 10**6), max_size=5, unique=True)):
        cands = []
        for i in range(draw(st.integers(0, 8))):
            lang, doc = draw(st.sampled_from(["vi", "zh", "en"])), draw(st.integers(1, 4))
            text = draw(TEXT)
            cands.append(Candidate(chunk_id=f"{lang}:{doc}#{i}", uid=f"{lang}:{doc}", doc_id=str(doc), start=i, end=i + 1,
                                   p_start=i, p_end=i + 1, score=0.5, text=text))
        out.append(QueryResult(qid=qid, query="q", candidates=cands))
    return out


@st.composite
def cfgs(draw):
    return BuildCfg(max_docs=draw(st.one_of(st.none(), st.integers(1, 4))), max_chunks=draw(st.one_of(st.none(), st.integers(1, 6))))


@hyp(max_examples=200, deadline=None)
@given(rs=results(), cfg=cfgs())
def test_built_submission_is_valid_and_never_invents_content(rs, cfg):
    items = build_items(rs, cfg)
    assert [i.id for i in items] == [r.qid for r in rs]
    for it, r in zip(items, rs):
        docs_in = {c.doc_id for c in r.candidates}
        assert set(it.relevant_docs) <= docs_in and len(set(it.relevant_docs)) == len(it.relevant_docs)
        assert cfg.max_docs is None or len(it.relevant_docs) <= cfg.max_docs
        assert cfg.max_chunks is None or len(it.relevant_chunks) <= cfg.max_chunks
        keys = [(c.doc_id, c.chunk_text) for c in it.relevant_chunks]
        assert len(set(keys)) == len(keys) and set(c.doc_id for c in it.relevant_chunks) <= set(it.relevant_docs)
        source = {(c.doc_id, c.text) for c in r.candidates}
        assert all(k in source for k in keys)                                      # chunk_text là nguyên văn một candidate
        if r.candidates:
            assert it.relevant_docs[0] == r.candidates[0].doc_id                   # doc đầu bảng không bị mất
    assert not [p for p in check_items(items, {r.qid for r in rs}, 10**6, build_counter("approx")) if p.level == "error"]


@hyp(max_examples=100, deadline=None)
@given(rs=results(), cfg=cfgs())
def test_json_and_zip_roundtrip_any_content(rs, cfg):
    items = build_items(rs, cfg)
    assert SUBMISSION.validate_json(SUBMISSION.dump_json(items)) == items
    with tempfile.TemporaryDirectory() as tmp:
        z = make_zip(write_json(items, Path(tmp) / "s.json"), Path(tmp) / "b.zip", "s.json")
        assert read_zip(z) == items