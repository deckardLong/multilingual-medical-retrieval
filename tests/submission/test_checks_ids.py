from factories import cand_of
from retrieval.results import QueryResult
from submission.checks import check_ids

KNOWN = {"1", "2", "3"}


def qr(qid, *cands):
    return QueryResult(qid=qid, query="q", candidates=list(cands))


def test_known_ids_pass():
    assert check_ids([qr(1, cand_of("vi:1", 0, "a"), cand_of("zh:2", 0, "b"))], KNOWN) == []


def test_unknown_vietnamese_or_chinese_id_is_an_error_naming_the_query():
    (p,) = check_ids([qr(4, cand_of("vi:99", 0, "a")), qr(5, cand_of("vi:1", 0, "a"))], KNOWN)
    assert p.level == "error" and p.qid == 4 and "99" in p.msg
    (p,) = check_ids([qr(6, cand_of("zh:77", 0, "a"))], KNOWN)
    assert p.qid == 6 and "77" in p.msg


def test_english_docs_are_checked_against_the_btc_list_too():
    assert check_ids([qr(1, cand_of("en:3", 0, "a"))], KNOWN) == []
    (p,) = check_ids([qr(2, cand_of("en:26739349", 0, "a"))], KNOWN)
    assert p.level == "error" and "26739349" in p.msg


def test_unknown_ids_are_counted_once_per_query():
    (p,) = check_ids([qr(1, cand_of("vi:90", 0, "a"), cand_of("vi:90", 1, "b"), cand_of("vi:91", 0, "c"))], KNOWN)
    assert "2 doc_id" in p.msg and "90, 91" in p.msg


def test_without_the_btc_list_the_check_is_skipped_with_one_warning():
    ps = check_ids([qr(1, cand_of("vi:99", 0, "a")), qr(2, cand_of("vi:98", 0, "a"))], None)
    assert [p.level for p in ps] == ["warning"] and ps[0].qid is None


def test_empty_results_and_empty_known_set():
    assert check_ids([], KNOWN) == []
    (p,) = check_ids([qr(1, cand_of("vi:1", 0, "a"))], set())
    assert p.level == "error"                                             # tập rỗng KHÁC "không có danh sách": mọi id đều lạ