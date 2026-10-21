import pyarrow as pa, pyarrow.parquet as pq
import pytest
from retrieval.results import load_queries
import json


def _write(tmp_path, **cols):
    p = tmp_path / "q.parquet"
    pq.write_table(pa.table(cols), p)
    return p


def test_load_queries(tmp_path):
    p = _write(tmp_path, id=[3, 4, 5], query=["a", "b", "c"])
    qs = load_queries(p, limit=2)
    assert [(q.qid, q.text) for q in qs] == [(3, "a"), (4, "b")]
    with pytest.raises(ValueError, match="cột"):
        load_queries(p, text_col="nope")


def test_all_rows_when_no_limit_and_order_preserved(tmp_path):
    p = _write(tmp_path, id=[9, 1, 5], query=["x", "y", "z"])
    assert [q.qid for q in load_queries(p)] == [9, 1, 5]


def test_limit_zero_gives_no_queries(tmp_path):
    assert load_queries(_write(tmp_path, id=[1], query=["a"]), limit=0) == []


def test_custom_columns_and_extra_columns_ignored(tmp_path):
    p = _write(tmp_path, qid=[1, 2], text=["a", "b"], lang=["vi", "zh"])
    assert [(q.qid, q.text) for q in load_queries(p, id_col="qid", text_col="text")] == [(1, "a"), (2, "b")]


def test_string_ids_are_converted_to_int(tmp_path):
    assert load_queries(_write(tmp_path, id=["7", "8"], query=["a", "b"]))[0].qid == 7


def test_non_numeric_id_is_an_error(tmp_path):
    with pytest.raises(ValueError):
        load_queries(_write(tmp_path, id=["abc"], query=["a"]))


def test_unicode_text_is_kept(tmp_path):
    assert load_queries(_write(tmp_path, id=[1], query=["肾结石症状 và triệu chứng"]))[0].text == "肾结石症状 và triệu chứng"


@pytest.mark.parametrize("texts", [[None], [""], ["   "]])
def test_blank_or_null_query_is_rejected(tmp_path, texts):
    with pytest.raises(ValueError, match="rỗng"):
        load_queries(_write(tmp_path, id=[1], query=texts))


def test_null_id_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="rỗng"):
        load_queries(_write(tmp_path, id=pa.array([None], pa.int64()), query=["a"]))


def test_error_names_the_row(tmp_path):
    with pytest.raises(ValueError, match="dòng 2"):
        load_queries(_write(tmp_path, id=[1, 2, 3], query=["a", "b", None]))


def test_blank_row_beyond_the_limit_is_not_an_error(tmp_path):
    assert len(load_queries(_write(tmp_path, id=[1, 2], query=["a", None]), limit=1)) == 1


def test_missing_column_message_lists_available_columns(tmp_path):
    with pytest.raises(ValueError, match="id.*query|query.*id"):
        load_queries(_write(tmp_path, id=[1], query=["a"]), id_col="qid")

def _jsonl(tmp_path, rows):
    p = tmp_path / "q.jsonl"
    p.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    return p


def test_btc_jsonl_example_loads(tmp_path):
    p = _jsonl(tmp_path, [{"id": 1, "query": "Cần làm gì đối với tình trạng tắc nghẽn đường tiết niệu do sỏi thận?"}])
    (q,) = load_queries(p)
    assert q.qid == 1 and q.text.startswith("Cần làm gì") and isinstance(q.qid, int)


def test_jsonl_limit_order_and_custom_columns(tmp_path):
    p = _jsonl(tmp_path, [{"qid": 9, "text": "a"}, {"qid": 1, "text": "b"}, {"qid": 5, "text": "c"}])
    assert [(q.qid, q.text) for q in load_queries(p, "qid", "text", limit=2)] == [(9, "a"), (1, "b")]


def test_jsonl_blank_or_missing_text_names_the_row(tmp_path):
    with pytest.raises(ValueError, match="dòng 1.*rỗng"):
        load_queries(_jsonl(tmp_path, [{"id": 1, "query": "a"}, {"id": 2}]))
    with pytest.raises(ValueError, match="rỗng"):
        load_queries(_jsonl(tmp_path, [{"id": 1, "query": "  "}]))


def test_jsonl_wrong_column_lists_the_available_ones(tmp_path):
    with pytest.raises(ValueError, match="id.*query|query.*id"):
        load_queries(_jsonl(tmp_path, [{"id": 1, "query": "a"}]), text_col="nope")


def test_jsonl_limit_zero_gives_no_queries_like_parquet(tmp_path):
    assert load_queries(_jsonl(tmp_path, [{"id": 1, "query": "a"}]), limit=0) == []