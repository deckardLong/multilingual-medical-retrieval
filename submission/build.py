"""Kết quả truy hồi (C2) → bài nộp (C3). Chỉ biến đổi, không chọn lại: chọn doc/chunk là việc của retrieval.select."""
from typing import Iterable
from retrieval.results import QueryResult
from .schema import SubChunk, SubItem
from .settings import BuildCfg


class SubmissionError(ValueError):
    """Dữ liệu đầu vào không thể đổi thành bài nộp hợp lệ."""


def build_item(r: QueryResult, cfg: BuildCfg) -> SubItem:
    # doc xếp theo thứ tự xuất hiện đầu tiên (C2 đã sắp doc tốt nhất trước)
    docs = list(dict.fromkeys(c.doc_id for c in r.candidates))[: cfg.max_docs]
    keep, seen, chunks = set(docs), set(), []
    for c in r.candidates:
        if c.doc_id not in keep:
            continue
        if c.text is None or not c.text.strip():
            raise SubmissionError(f"truy vấn {r.qid}: chunk {c.chunk_id} không có text; chạy lại bước truy hồi")
        if (c.doc_id, c.text) in seen:                 # cùng doc_id (vi:7 và zh:7) và cùng nội dung: chỉ nộp một lần
            continue
        seen.add((c.doc_id, c.text))
        chunks.append(SubChunk(doc_id=c.doc_id, chunk_text=c.text))
    return SubItem(id=r.qid, relevant_docs=docs, relevant_chunks=chunks[: cfg.max_chunks])


def build_items(results: Iterable[QueryResult], cfg: BuildCfg) -> list[SubItem]:
    return [build_item(r, cfg) for r in results]