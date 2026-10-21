from typing import Any, cast

from common.schema import Chunk
from retrieval.chunking.validate import validate_doc_chunks, coverage
from factories import make_doc

DOC = make_doc("T\nabc def.\nghi jkl.\n")


def ch(start, end, **kw):
    d = dict(chunk_id="vi:1#0", uid="vi:1", doc_id="1", lang="vi", start=start, end=end, p_start=start, p_end=end,
             heading="", ctx="", text=DOC.text[start:end], n_tokens=3, chunker_ver="v")
    d.update(kw); return Chunk(**cast(Any, d))


def test_ok_and_each_failure_mode():
    assert validate_doc_chunks(DOC, [ch(2, 10), ch(11, 19)]) == []
    assert validate_doc_chunks(DOC, [ch(2, 10, text="sai")])                          # text khác doc.text[start:end]
    assert validate_doc_chunks(DOC, [ch(2, 999, text="x")])                           # ngoài phạm vi
    assert validate_doc_chunks(DOC, [ch(2, 10, p_start=5)])                           # cha không bao con
    assert validate_doc_chunks(DOC, [ch(10, 11, text=DOC.text[10:11])])               # chunk toàn khoảng trắng
    assert validate_doc_chunks(DOC, [ch(11, 19), ch(2, 10)])                          # thứ tự lùi


def test_coverage():
    assert coverage(DOC, [ch(2, 10), ch(11, 19)]) == 1.0
    assert 0 < coverage(DOC, [ch(2, 10)]) < 1.0
    assert coverage(make_doc("Chỉ tiêu đề"), []) == 1.0