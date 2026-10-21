import pytest
from common.schema import Candidate
from retrieval.select import select, pick_docs, Selection
from retrieval.select.docs import group_by_uid


def c(uid, i, score, start=0, end=10, doc_id=None):
    return Candidate(chunk_id=f"{uid}#{i}", uid=uid, doc_id=doc_id or uid.split(":")[1], start=start, end=end,
                     p_start=start, p_end=end, score=score, text="t")


@pytest.fixture
def scfg(settings):
    return settings.retrieve.select.model_copy(update=dict(max_docs=3, min_score=None, rel_drop=None, chunks_per_doc=2))


def test_max_docs_and_order(scfg):
    cs = [c(f"vi:{i}", 0, 1 - i / 10) for i in range(6)]
    assert select(cs, scfg).doc_ids == ["0", "1", "2"]


def test_input_order_does_not_matter(scfg):
    cs = [c(f"vi:{i}", 0, 1 - i / 10) for i in range(6)]
    assert select(list(reversed(cs)), scfg).doc_ids == ["0", "1", "2"]


def test_rel_drop_and_min_score(scfg):
    cs = [c("vi:1", 0, 0.9), c("vi:2", 0, 0.5), c("vi:3", 0, 0.3)]
    assert select(cs, scfg.model_copy(update=dict(rel_drop=0.5))).doc_ids == ["1", "2"]          # 0.3 < 0.45
    assert select(cs, scfg.model_copy(update=dict(min_score=0.6))).doc_ids == ["1"]


def test_top_doc_always_kept_even_below_threshold(scfg):
    cs = [c("vi:1", 0, 0.2), c("vi:2", 0, 0.1)]
    assert select(cs, scfg.model_copy(update=dict(min_score=0.5))).doc_ids == ["1"]


def test_doc_score_is_best_chunk_and_chunks_per_doc(scfg):
    cs = [c("vi:1", 0, 0.4, 0, 5), c("vi:1", 1, 0.95, 10, 20), c("vi:1", 2, 0.5, 30, 40), c("vi:1", 3, 0.45, 50, 60),
          c("vi:2", 0, 0.8)]
    s = select(cs, scfg)
    assert s.doc_ids == ["1", "2"]
    assert [x.chunk_id for x in s.chunks if x.uid == "vi:1"] == ["vi:1#1", "vi:1#2"]


def test_one_strong_chunk_outranks_a_doc_with_many_medium_chunks(scfg):
    cs = [c("vi:1", i, 0.6, i * 20, i * 20 + 10) for i in range(5)] + [c("vi:2", 0, 0.9)]
    assert select(cs, scfg).doc_ids == ["2", "1"]                           # điểm doc = chunk tốt nhất, không cộng dồn


def test_chunks_are_grouped_by_doc_in_rank_order(scfg):
    cs = [c("vi:1", 0, 0.9, 0, 10), c("vi:1", 1, 0.3, 20, 30), c("vi:2", 0, 0.8)]
    assert [x.chunk_id for x in select(cs, scfg).chunks] == ["vi:1#0", "vi:1#1", "vi:2#0"]     # 0.3 vẫn đứng trước doc 2


def test_chunks_per_doc_one(scfg):
    cs = [c("vi:1", 0, 0.9, 0, 10), c("vi:1", 1, 0.8, 20, 30), c("vi:2", 0, 0.7)]
    assert [x.chunk_id for x in select(cs, scfg.model_copy(update=dict(chunks_per_doc=1))).chunks] == ["vi:1#0", "vi:2#0"]


def test_overlapping_chunks_deduped_inside_select(scfg):
    cs = [c("vi:1", 0, 0.9, 0, 100), c("vi:1", 1, 0.8, 10, 90), c("vi:1", 2, 0.7, 200, 300)]
    assert [x.chunk_id for x in select(cs, scfg.model_copy(update=dict(chunks_per_doc=3))).chunks] == ["vi:1#0", "vi:1#2"]


def test_same_doc_id_in_two_langs_reported_once(scfg):
    s = select([c("vi:7", 0, 0.9, doc_id="7"), c("zh:7", 0, 0.8, doc_id="7")], scfg)
    assert s.doc_ids == ["7"] and len(s.chunks) == 2


def test_score_ties_keep_input_order(scfg):
    cs = [c("vi:2", 0, 0.5), c("vi:1", 0, 0.5), c("vi:3", 0, 0.5)]
    assert select(cs, scfg).doc_ids == ["2", "1", "3"]


def test_selected_chunks_are_the_original_candidates(scfg):
    cs = [c("vi:1", 0, 0.9)]
    assert select(cs, scfg).chunks == cs and select(cs, scfg).chunks[0].score == 0.9


def test_input_is_not_modified(scfg):
    cs = [c("vi:2", 0, 0.5), c("vi:1", 0, 0.9)]
    select(cs, scfg)
    assert [x.chunk_id for x in cs] == ["vi:2#0", "vi:1#0"]


def test_empty(scfg):
    s = select([], scfg)
    assert isinstance(s, Selection) and s.doc_ids == [] and s.chunks == [] and pick_docs([], scfg) == []


def test_group_by_uid_orders_docs_by_best_chunk_and_chunks_by_score():
    cs = [c("vi:1", 0, 0.3), c("vi:2", 0, 0.9), c("vi:1", 1, 0.8), c("vi:2", 1, 0.1)]
    g = group_by_uid(cs)
    assert list(g) == ["vi:2", "vi:1"]
    assert [x.chunk_id for x in g["vi:1"]] == ["vi:1#1", "vi:1#0"] and [x.chunk_id for x in g["vi:2"]] == ["vi:2#0", "vi:2#1"]