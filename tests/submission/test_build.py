import pytest
from factories import cand_of
from retrieval.results import QueryResult
from submission import SubmissionError, build_item, build_items
from submission.settings import BuildCfg


def qr(qid, *cands):
    return QueryResult(qid=qid, query="q", candidates=list(cands))


def cfg(**kw):
    return BuildCfg(**{"max_docs": None, "max_chunks": None, **kw})


def test_docs_in_order_of_first_appearance_and_chunks_kept():
    it = build_item(qr(5, cand_of("vi:3", 0, "a"), cand_of("vi:3", 1, "b"), cand_of("vi:1", 0, "c")), cfg())
    assert it.id == 5 and it.relevant_docs == ["3", "1"]
    assert [(c.doc_id, c.chunk_text) for c in it.relevant_chunks] == [("3", "a"), ("3", "b"), ("1", "c")]


def test_chunk_text_is_copied_verbatim_including_whitespace():
    text = "  Triệu chứng\n\tkhát nhiều  \n"
    assert build_item(qr(1, cand_of("vi:1", 0, text)), cfg()).relevant_chunks[0].chunk_text == text


def test_empty_candidates_give_empty_lists():
    it = build_item(qr(8), cfg())
    assert it.id == 8 and it.relevant_docs == [] and it.relevant_chunks == []


def test_same_doc_id_in_two_languages_is_one_doc_and_identical_text_is_sent_once():
    it = build_item(qr(1, cand_of("vi:7", 0, "x"), cand_of("zh:7", 0, "x"), cand_of("zh:7", 1, "y")), cfg())
    assert it.relevant_docs == ["7"] and [c.chunk_text for c in it.relevant_chunks] == ["x", "y"]


def test_same_text_in_different_docs_is_kept_for_each_doc():
    it = build_item(qr(1, cand_of("vi:1", 0, "x"), cand_of("vi:2", 0, "x")), cfg())
    assert [c.doc_id for c in it.relevant_chunks] == ["1", "2"]


def test_max_docs_drops_later_docs_and_their_chunks():
    cs = [cand_of("vi:1", 0, "a"), cand_of("vi:1", 1, "b"), cand_of("vi:2", 0, "c"), cand_of("vi:3", 0, "d")]
    it = build_item(qr(1, *cs), cfg(max_docs=2))
    assert it.relevant_docs == ["1", "2"] and [c.chunk_text for c in it.relevant_chunks] == ["a", "b", "c"]


def test_max_chunks_keeps_the_first_chunks():
    cs = [cand_of("vi:1", 0, "a"), cand_of("vi:1", 1, "b"), cand_of("vi:2", 0, "c")]
    it = build_item(qr(1, *cs), cfg(max_chunks=2))
    assert [c.chunk_text for c in it.relevant_chunks] == ["a", "b"] and it.relevant_docs == ["1", "2"]


def test_max_docs_larger_than_available_changes_nothing():
    cs = [cand_of("vi:1", 0, "a")]
    assert build_item(qr(1, *cs), cfg(max_docs=9, max_chunks=9)) == build_item(qr(1, *cs), cfg())


@pytest.mark.parametrize("text", [None, "", "   \n"])
def test_candidate_without_text_cannot_be_submitted(text):
    c = cand_of("vi:1", 0, "x").model_copy(update=dict(text=text))
    with pytest.raises(SubmissionError, match="truy vấn 4.*vi:1#0"):
        build_item(qr(4, c), cfg())


def test_chunk_of_a_dropped_doc_without_text_is_not_an_error():
    bad = cand_of("vi:2", 0, "x").model_copy(update=dict(text=None))
    assert build_item(qr(1, cand_of("vi:1", 0, "a"), bad), cfg(max_docs=1)).relevant_docs == ["1"]


def test_build_items_keeps_query_order_and_count():
    items = build_items([qr(9, cand_of("vi:1", 0, "a")), qr(2), qr(5, cand_of("vi:2", 0, "b"))], cfg())
    assert [i.id for i in items] == [9, 2, 5]


def test_build_items_accepts_a_generator_and_empty_input():
    assert build_items((qr(i) for i in range(3)), cfg()) and build_items([], cfg()) == []


def test_input_results_are_not_modified():
    r = qr(1, cand_of("vi:1", 0, "a"), cand_of("vi:1", 0, "a"))
    before = r.model_dump()
    build_item(r, cfg(max_docs=1, max_chunks=1))
    assert r.model_dump() == before


@pytest.mark.parametrize("kw", [dict(max_docs=0), dict(max_chunks=0), dict(max_docs=-1)])
def test_build_cfg_rejects_non_positive_limits(kw):
    with pytest.raises(ValueError):
        cfg(**kw)