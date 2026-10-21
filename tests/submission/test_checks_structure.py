import pytest
from submission import SubChunk, SubItem
from submission.checks import Problem, Report, check_items


def it(qid, docs=("1",), chunks=(("1", "nội dung"),)):
    return SubItem(id=qid, relevant_docs=list(docs), relevant_chunks=[SubChunk(doc_id=d, chunk_text=t) for d, t in chunks])


def run(items, words, expected=None, max_tokens=1024):
    return check_items(items, expected, max_tokens, words)


def levels(ps):
    return sorted(p.level for p in ps)


def test_clean_submission_has_no_problems(words):
    assert run([it(1), it(2)], words, {1, 2}) == []


def test_duplicate_query_ids_are_an_error(words):
    ps = run([it(1), it(1), it(2)], words)
    assert levels(ps) == ["error"] and "lặp" in ps[0].msg and "1" in ps[0].msg


def test_missing_queries_are_an_error_with_count(words):
    ps = run([it(1)], words, {1, 2, 3})
    assert levels(ps) == ["error"] and "thiếu 2" in ps[0].msg and "2, 3" in ps[0].msg


def test_unexpected_ids_are_an_error(words):
    ps = run([it(1), it(99)], words, {1})
    assert levels(ps) == ["error"] and "99" in ps[0].msg


def test_completeness_is_skipped_without_expected_ids(words):
    assert run([it(1)], words, None) == []


def test_long_list_of_missing_ids_is_abbreviated(words):
    (p,) = run([], words, set(range(1000)))
    assert "(+995)" in p.msg and len(p.msg) < 200


@pytest.mark.parametrize("bad", ["vi:1", "abc", "", "１２", "1.5", "-3", " 7", "3 "])
def test_doc_id_must_be_digits(words, bad):
    ps = run([it(1, docs=[bad], chunks=[])], words)
    assert any(p.level == "error" and "chữ số" in p.msg and p.qid == 1 for p in ps)


def test_chunk_doc_id_format_is_checked_too(words):
    ps = run([it(1, docs=["1"], chunks=[("x", "t")])], words)
    assert any(p.level == "error" and "chữ số" in p.msg for p in ps)


@pytest.mark.parametrize("ok", ["0", "7", "26739349", "007"])
def test_numeric_doc_ids_are_fine(words, ok):
    assert run([it(1, docs=[ok], chunks=[(ok, "t")])], words) == []


def test_duplicate_relevant_docs_are_an_error(words):
    ps = run([it(1, docs=["1", "1"], chunks=[])], words)
    assert any(p.level == "error" and "lặp" in p.msg for p in ps)


@pytest.mark.parametrize("text", ["", "   ", "\n\t"])
def test_blank_chunk_text_is_an_error(words, text):
    ps = run([it(1, chunks=[("1", text), ("1", "tốt")])], words)
    assert [p.level for p in ps] == ["error"] and "1 chunk_text rỗng" in ps[0].msg


def test_chunk_of_a_doc_missing_from_relevant_docs_is_only_a_warning(words):
    ps = run([it(1, docs=["1"], chunks=[("1", "a"), ("2", "b")])], words)
    assert levels(ps) == ["warning"] and "2" in ps[0].msg


def test_chunk_length_limit_is_inclusive(words):
    assert run([it(1, chunks=[("1", "a b c")])], words, max_tokens=3) == []
    ps = run([it(1, chunks=[("1", "a b c d")])], words, max_tokens=3)
    assert levels(ps) == ["warning"] and "1 chunk_text dài" in ps[0].msg


def test_query_without_any_result_is_a_warning(words):
    ps = run([it(1, docs=[], chunks=[])], words)
    assert levels(ps) == ["warning"] and ps[0].qid == 1


def test_query_with_docs_but_no_chunks_is_not_flagged(words):
    assert run([it(1, docs=["1"], chunks=[])], words) == []


def test_problem_text_names_query_and_level():
    assert str(Problem("error", "hỏng", 7)) == "ERROR   [qid 7] hỏng"
    assert str(Problem("warning", "chú ý")) == "WARNING chú ý"


def test_report_splits_errors_and_warnings():
    r = Report((Problem("error", "e"), Problem("warning", "w")))
    assert not r.ok and [p.msg for p in r.errors] == ["e"] and [p.msg for p in r.warnings] == ["w"]
    assert Report((Problem("warning", "w"),)).ok and Report(()).ok
    assert str(r).splitlines() == ["ERROR   e", "WARNING w"]