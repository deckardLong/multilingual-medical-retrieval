import csv
from submission.log import FIELDS, append_log


def rows(p):
    return list(csv.DictReader(open(p, encoding="utf-8", newline="")))


def test_header_written_once_and_rows_appended(tmp_path):
    p = tmp_path / "r" / "log.csv"
    append_log(p, dict(zip="a.zip", n_queries=3, note="thử"))
    append_log(p, dict(zip="b.zip", n_queries=4))
    assert p.read_text("utf-8").count("time,zip") == 1
    assert [r["zip"] for r in rows(p)] == ["a.zip", "b.zip"]


def test_all_columns_exist_and_missing_values_are_blank(tmp_path):
    p = tmp_path / "log.csv"
    append_log(p, dict(zip="a.zip"))
    (r,) = rows(p)
    assert list(r) == FIELDS and r["public_score"] == "" and r["note"] == ""


def test_unicode_and_commas_in_the_note_survive(tmp_path):
    p = tmp_path / "log.csv"
    append_log(p, dict(note='max_docs=5, "rel_drop" 0.5 — thử nghiệm'))
    assert rows(p)[0]["note"] == 'max_docs=5, "rel_drop" 0.5 — thử nghiệm'


def test_extra_keys_are_ignored(tmp_path):
    p = tmp_path / "log.csv"
    append_log(p, dict(zip="a.zip", khong_co="x"))
    assert "khong_co" not in rows(p)[0]


def test_an_empty_existing_file_still_gets_a_header(tmp_path):
    p = tmp_path / "log.csv"; p.write_text("")
    append_log(p, dict(zip="a.zip"))
    assert rows(p)[0]["zip"] == "a.zip"