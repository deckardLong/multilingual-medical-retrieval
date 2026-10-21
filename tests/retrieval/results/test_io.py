import json
import pytest
from factories import cand
from retrieval.results import QueryResult, write_results, read_results, write_json


def test_roundtrip_and_atomic(tmp_path):
    rs = [QueryResult(qid=1, query="q1", candidates=[cand(0, "a", ctx="T")]), QueryResult(qid=2, query="q2", candidates=[])]
    p = tmp_path / "o" / "r.jsonl"
    assert write_results(p, rs) == 2
    back = list(read_results(p))
    assert back == rs and back[0].candidates[0].ctx == "T" and not list(p.parent.glob("*.tmp"))


def test_one_json_object_per_line_with_unicode_kept(tmp_path):
    p = tmp_path / "r.jsonl"
    write_results(p, [QueryResult(qid=1, query="triệu chứng 糖尿病", candidates=[])])
    lines = p.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1 and "triệu chứng 糖尿病" in lines[0] and json.loads(lines[0])["qid"] == 1


def test_empty_results_make_an_empty_file(tmp_path):
    p = tmp_path / "r.jsonl"
    assert write_results(p, []) == 0 and p.read_text() == "" and list(read_results(p)) == []


def test_accepts_a_generator(tmp_path):
    p = tmp_path / "r.jsonl"
    assert write_results(p, (QueryResult(qid=i, query="q", candidates=[]) for i in range(3))) == 3


def test_blank_lines_are_skipped_when_reading(tmp_path):
    p = tmp_path / "r.jsonl"
    write_results(p, [QueryResult(qid=1, query="a", candidates=[])])
    p.write_text(p.read_text() + "\n\n   \n", encoding="utf-8")
    assert [r.qid for r in read_results(p)] == [1]


def test_candidate_fields_survive_the_roundtrip(tmp_path):
    c = cand(3, "nội dung", ctx="Bài | Mục", score=0.25)
    p = tmp_path / "r.jsonl"
    write_results(p, [QueryResult(qid=1, query="q", candidates=[c])])
    assert next(read_results(p)).candidates[0] == c


def test_failure_midway_keeps_the_previous_file(tmp_path):
    p = tmp_path / "r.jsonl"
    write_results(p, [QueryResult(qid=1, query="cũ", candidates=[])])
    def broken():
        yield QueryResult(qid=2, query="mới", candidates=[])
        raise RuntimeError("giữa chừng")
    with pytest.raises(RuntimeError):
        write_results(p, broken())
    assert [r.query for r in read_results(p)] == ["cũ"]                      # file cũ còn nguyên, không bị ghi dở


def test_corrupt_line_is_an_error(tmp_path):
    p = tmp_path / "r.jsonl"
    p.write_text("{không phải json\n", encoding="utf-8")
    with pytest.raises(Exception):
        list(read_results(p))


def test_write_json_unicode_indent_and_atomic(tmp_path):
    p = tmp_path / "sub" / "card.json"
    write_json(p, {"tên": "triệu chứng", "n": 2})
    text = p.read_text(encoding="utf-8")
    assert "triệu chứng" in text and json.loads(text) == {"tên": "triệu chứng", "n": 2} and "\n  " in text
    assert not list(p.parent.glob("*.tmp"))


def test_write_json_overwrites(tmp_path):
    p = tmp_path / "c.json"
    write_json(p, {"a": 1}); write_json(p, {"a": 2})
    assert json.loads(p.read_text()) == {"a": 2}