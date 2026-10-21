import json
import pyarrow as pa, pyarrow.parquet as pq
import pytest
from submission.sources import load_id_set


def test_ids_from_btc_style_jsonl_become_strings(tmp_path):
    p = tmp_path / "urls.jsonl"
    p.write_text("\n".join(json.dumps({"id": i, "url": f"https://x/{i}"}) for i in (1, 22, 333)), "utf-8")
    assert load_id_set(p) == {"1", "22", "333"}


def test_ids_from_parquet(tmp_path):
    p = tmp_path / "ids.parquet"
    pq.write_table(pa.table({"id": [5, 6], "url": ["a", "b"]}), p)
    assert load_id_set(p) == {"5", "6"}


def test_null_ids_are_ignored_and_duplicates_collapse(tmp_path):
    p = tmp_path / "ids.jsonl"
    p.write_text('{"id": 1}\n{"id": null}\n{"id": 1}\n{"url": "x"}\n', "utf-8")
    assert load_id_set(p) == {"1"}


def test_file_without_id_column_is_an_error_listing_columns(tmp_path):
    p = tmp_path / "ids.jsonl"; p.write_text('{"doc": 1}\n', "utf-8")
    with pytest.raises(ValueError, match="'id'.*doc"):
        load_id_set(p)