import json
import pytest
from pydantic import ValidationError
from submission import SUBMISSION, SubChunk, SubItem

# ví dụ nguyên văn trong đề bài
BTC_EXAMPLE = """[{"id": 1, "relevant_docs": ["doc_id1", "doc_id2"],
  "relevant_chunks": [{"doc_id": "doc_id1", "chunk_text": "Đoạn nội dung liên quan thứ nhất."},
                      {"doc_id": "doc_id2", "chunk_text": "Đoạn nội dung liên quan được trích từ tài liệu doc_id2."}]}]"""


def item(**kw):
    return {"id": 1, "relevant_docs": ["1"], "relevant_chunks": [{"doc_id": "1", "chunk_text": "t"}], **kw}


def test_btc_example_is_valid():
    (it,) = SUBMISSION.validate_json(BTC_EXAMPLE)
    assert it.id == 1 and it.relevant_docs == ["doc_id1", "doc_id2"] and it.relevant_chunks[1].doc_id == "doc_id2"


@pytest.mark.parametrize("bad_id", ["1", 1.5, 1.0, True, None])
def test_id_must_be_a_real_integer(bad_id):
    with pytest.raises(ValidationError):
        SUBMISSION.validate_python([item(id=bad_id)])


@pytest.mark.parametrize("bad", [dict(relevant_docs=[123]), dict(relevant_chunks=[{"doc_id": 1, "chunk_text": "t"}]),
                                 dict(relevant_chunks=[{"doc_id": "1", "chunk_text": None}]),
                                 dict(relevant_chunks=[{"doc_id": b"1", "chunk_text": "t"}]), dict(relevant_docs=[b"1"])])
def test_ids_and_texts_must_be_strings(bad):
    with pytest.raises(ValidationError):
        SUBMISSION.validate_python([item(**bad)])


@pytest.mark.parametrize("missing", ["id", "relevant_docs", "relevant_chunks"])
def test_every_field_is_required(missing):
    d = item(); del d[missing]
    with pytest.raises(ValidationError):
        SUBMISSION.validate_python([d])


def test_unknown_fields_are_rejected():
    with pytest.raises(ValidationError):
        SUBMISSION.validate_python([item(score=0.9)])
    with pytest.raises(ValidationError):
        SUBMISSION.validate_python([item(relevant_chunks=[{"doc_id": "1", "chunk_text": "t", "start": 0}])])


def test_empty_lists_are_allowed_at_both_levels():
    (it,) = SUBMISSION.validate_python([item(relevant_docs=[], relevant_chunks=[])])
    assert it.relevant_docs == [] and it.relevant_chunks == []


def test_empty_submission_is_valid_json_list():
    assert SUBMISSION.dump_json([]) == b"[]"


def test_dump_keeps_unicode_and_roundtrips():
    items = [SubItem(id=3, relevant_docs=["9"], relevant_chunks=[SubChunk(doc_id="9", chunk_text='triệu chứng 糖尿病 "trích dẫn"\nxuống dòng')])]
    raw = SUBMISSION.dump_json(items)
    assert "triệu chứng 糖尿病".encode("utf-8") in raw                    # không bị thoát \uXXXX
    assert SUBMISSION.validate_json(raw) == items
    assert json.loads(raw)[0]["relevant_chunks"][0]["chunk_text"].endswith("xuống dòng")


def test_field_names_in_output_match_the_spec_exactly():
    raw = json.loads(SUBMISSION.dump_json([SubItem(id=1, relevant_docs=["1"], relevant_chunks=[SubChunk(doc_id="1", chunk_text="t")])]))
    assert list(raw[0]) == ["id", "relevant_docs", "relevant_chunks"] and list(raw[0]["relevant_chunks"][0]) == ["doc_id", "chunk_text"]