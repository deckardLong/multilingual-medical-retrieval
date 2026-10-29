import csv
import pytest
from factories import cand_of
from retrieval.results import QueryResult
from submission import SubmissionError, SubmissionRejected, make_submission
from submission.pack import read_zip, sha256

KNOWN = {"1", "2", "3"}


def qr(qid, *cands):
    return QueryResult(qid=qid, query="q", candidates=list(cands))


RESULTS = [qr(1, cand_of("vi:1", 0, "a"), cand_of("vi:1", 1, "b"), cand_of("zh:2", 0, "c")),
           qr(2, cand_of("en:3", 0, "pubmed"))]


def make(cfg, tmp_path, results=RESULTS, expected={1, 2}, known=KNOWN, **kw):
    return make_submission(cfg, results, tmp_path / "out", kw.pop("name", "run1"), expected, known, **kw)


def test_happy_path_writes_only_the_zip_and_it_reads_back(submit_cfg, tmp_path):
    res = make(submit_cfg, tmp_path)
    assert res["zip"] == tmp_path / "out" / "run1.zip" and [p.name for p in (tmp_path / "out").iterdir()] == ["run1.zip"]
    items = read_zip(res["zip"])
    assert [i.id for i in items] == [1, 2] and items[0].relevant_docs == ["1", "2"] and items[1].relevant_docs == ["3"]
    assert [c.chunk_text for c in items[0].relevant_chunks] == ["a", "b", "c"]


def test_zip_over_the_size_limit_is_deleted_and_rejected_without_logging(submit_cfg, tmp_path):
    log = tmp_path / "log.csv"
    with pytest.raises(SubmissionRejected, match="vượt giới hạn"):
        make(submit_cfg.model_copy(update={"max_zip_mb": 1e-6}), tmp_path, log_csv=log)
    assert list((tmp_path / "out").iterdir()) == [] and not log.exists()


def test_stats_and_digest(submit_cfg, tmp_path):
    res = make(submit_cfg, tmp_path)
    assert (res["n_queries"], res["docs_total"], res["chunks_total"], res["queries_without_docs"]) == (2, 3, 4, 0)
    assert res["sha256"] == sha256(res["zip"]) and res["warnings"] == []


def test_missing_query_is_rejected_and_nothing_is_written(submit_cfg, tmp_path):
    log = tmp_path / "log.csv"
    with pytest.raises(SubmissionRejected, match="thiếu 1") as e:
        make(submit_cfg, tmp_path, results=RESULTS[:1], log_csv=log)
    assert e.value.report.errors and not (tmp_path / "out").exists() and not log.exists()


def test_unknown_doc_ids_are_dropped_with_one_warning(submit_cfg, tmp_path):
    res = make(submit_cfg, tmp_path, results=[qr(1, cand_of("vi:99", 0, "a"), cand_of("vi:1", 0, "b")), RESULTS[1]])
    item = read_zip(res["zip"])[0]
    assert item.relevant_docs == ["1"] and [c.doc_id for c in item.relevant_chunks] == ["1"]
    (w,) = [w for w in res["warnings"] if "không thuộc danh sách" in w.msg]
    assert "bỏ 1 doc_id" in w.msg and "99" in w.msg


def test_all_problems_are_reported_together(submit_cfg, tmp_path):
    with pytest.raises(SubmissionRejected) as e:
        make(submit_cfg, tmp_path, results=[qr(1, cand_of("vi:99", 0, "a"))])
    assert len(e.value.report.errors) == 1 and "thiếu 1" in e.value.report.errors[0].msg
    assert any("không thuộc danh sách" in w.msg for w in e.value.report.warnings)


def test_without_known_ids_or_expected_ids_it_still_builds_but_warns(submit_cfg, tmp_path):
    res = make(submit_cfg, tmp_path, expected=None, known=None)
    assert len(res["warnings"]) == 1 and "danh sách id" in res["warnings"][0].msg


def test_empty_query_result_is_allowed_and_counted(submit_cfg, tmp_path):
    res = make(submit_cfg, tmp_path, results=[RESULTS[0], qr(2)])
    assert res["queries_without_docs"] == 1 and any(w.qid == 2 for w in res["warnings"])
    assert read_zip(res["zip"])[1].relevant_chunks == []


def test_candidate_without_text_raises_before_writing(submit_cfg, tmp_path):
    bad = cand_of("vi:1", 0, "a").model_copy(update=dict(text=None))
    with pytest.raises(SubmissionError):
        make(submit_cfg, tmp_path, results=[qr(1, bad), RESULTS[1]])
    assert not (tmp_path / "out").exists()


def test_build_limits_from_the_config_are_applied(submit_cfg, tmp_path):
    cfg = submit_cfg.model_copy(update=dict(build=submit_cfg.build.model_copy(update=dict(max_docs=1))))
    items = read_zip(make(cfg, tmp_path)["zip"])
    assert items[0].relevant_docs == ["1"] and [c.chunk_text for c in items[0].relevant_chunks] == ["a", "b"]


def test_log_row_is_appended_only_on_success(submit_cfg, tmp_path):
    log = tmp_path / "log.csv"
    make(submit_cfg, tmp_path, log_csv=log, note="lần đầu")
    make(submit_cfg, tmp_path, name="run2", log_csv=log)
    rows = list(csv.DictReader(open(log, encoding="utf-8", newline="")))
    assert [r["zip"] for r in rows] == ["run1.zip", "run2.zip"] and rows[0]["note"] == "lần đầu"
    assert rows[0]["n_queries"] == "2" and rows[0]["chunks_total"] == "4" and rows[0]["time"]


def test_no_log_when_not_requested(submit_cfg, tmp_path):
    make(submit_cfg, tmp_path)
    assert not list(tmp_path.glob("*.csv"))


def test_resubmitting_replaces_the_previous_zip_of_the_same_name(submit_cfg, tmp_path):
    make(submit_cfg, tmp_path)
    make(submit_cfg, tmp_path, results=[RESULTS[0], qr(2)])
    assert read_zip(tmp_path / "out" / "run1.zip")[1].relevant_docs == []


def test_a_zip_that_does_not_read_back_identically_is_refused(submit_cfg, tmp_path, monkeypatch):
    from submission import run as run_module
    monkeypatch.setattr(run_module, "read_zip", lambda p: [])
    with pytest.raises(RuntimeError, match="không khớp"):
        make(submit_cfg, tmp_path)


def test_overlong_chunks_are_reported_as_warnings_using_the_configured_limit(submit_cfg, tmp_path):
    long_text = " ".join(["từ"] * 30)
    cfg = submit_cfg.model_copy(update=dict(check=submit_cfg.check.model_copy(update=dict(max_chunk_tokens=5))))
    res = make(cfg, tmp_path, results=[qr(1, cand_of("vi:1", 0, long_text)), RESULTS[1]])
    assert any("dài hơn ~5 token" in w.msg and w.qid == 1 for w in res["warnings"])