import json
import pyarrow as pa, pyarrow.parquet as pq
import pytest
from common.io.tables import read_table


def jsonl(tmp_path, rows, name="t.jsonl"):
    p = tmp_path / name
    p.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    return p


def test_jsonl_columns_and_values(tmp_path):
    names, cols = read_table(jsonl(tmp_path, [{"id": 1, "url": "u1"}, {"id": 2, "url": "u2"}]))
    assert names == ["id", "url"] and cols == {"id": [1, 2], "url": ["u1", "u2"]}


def test_only_wanted_columns_are_loaded_but_all_names_reported(tmp_path):
    names, cols = read_table(jsonl(tmp_path, [{"id": 1, "url": "u"}]), wanted=["id", "khong_co"])
    assert names == ["id", "url"] and list(cols) == ["id"]


def test_jsonl_limit_stops_early_and_zero_gives_nothing(tmp_path):
    p = jsonl(tmp_path, [{"id": i} for i in range(5)])
    assert read_table(p, limit=2)[1] == {"id": [0, 1]} and read_table(p, limit=0)[1] == {"id": []}


def test_jsonl_blank_lines_are_skipped(tmp_path):
    p = tmp_path / "t.jsonl"; p.write_text('\n{"id": 1}\n   \n{"id": 2}\n\n', encoding="utf-8")
    assert read_table(p)[1]["id"] == [1, 2]


def test_jsonl_missing_key_becomes_none_so_callers_can_report_the_row(tmp_path):
    names, cols = read_table(jsonl(tmp_path, [{"id": 1, "q": "a"}, {"id": 2}]))
    assert cols["q"] == ["a", None] and names == ["id", "q"]


def test_jsonl_unicode_is_kept(tmp_path):
    assert read_table(jsonl(tmp_path, [{"q": "糖尿病 và triệu chứng"}]))[1]["q"] == ["糖尿病 và triệu chứng"]


def test_jsonl_line_that_is_not_an_object_is_an_error(tmp_path):
    p = tmp_path / "t.jsonl"; p.write_text('{"id": 1}\n[1, 2]\n', encoding="utf-8")
    with pytest.raises(ValueError, match="dòng 2"):
        read_table(p)


def test_jsonl_corrupt_line_is_an_error(tmp_path):
    p = tmp_path / "t.jsonl"; p.write_text("{không phải json\n", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        read_table(p)


@pytest.mark.parametrize("name", ["t.JSONL", "t.ndjson"])
def test_jsonl_suffix_variants(tmp_path, name):
    assert read_table(jsonl(tmp_path, [{"id": 7}], name))[1] == {"id": [7]}


def test_empty_jsonl(tmp_path):
    p = tmp_path / "t.jsonl"; p.write_text("")
    assert read_table(p) == ([], {})


def test_parquet_columns_wanted_and_limit(tmp_path):
    p = tmp_path / "t.parquet"
    pq.write_table(pa.table({"id": [1, 2, 3], "url": ["a", "b", "c"]}), p)
    names, cols = read_table(p, wanted=["id"], limit=2)
    assert names == ["id", "url"] and cols == {"id": [1, 2]}
    assert read_table(p, limit=0)[1] == {"id": [], "url": []}