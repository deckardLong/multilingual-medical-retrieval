"""Kết quả truy hồi (C2) → bài nộp (C3). Chỉ biến đổi, không chọn lại: chọn doc/chunk là việc của retrieval.select."""
from typing import Iterable
from retrieval.results import QueryResult
from .schema import SubChunk, SubItem
from .settings import BuildCfg
from .expand import Expander
from .split import split_text


class SubmissionError(ValueError):
    """Dữ liệu đầu vào không thể đổi thành bài nộp hợp lệ."""


def build_item(r: QueryResult, cfg: BuildCfg, expander: Expander | None = None) -> SubItem:
    # doc xếp theo thứ tự xuất hiện đầu tiên (C2 đã sắp doc tốt nhất trước)
    docs = list(dict.fromkeys(c.doc_id for c in r.candidates))[: cfg.max_docs]
    keep, seen, chunks = set(docs), set(), []
    windows: dict[str, list[tuple[int, int]]] = {}
    for c in r.candidates:
        if c.doc_id not in keep:
            continue
        if c.text is None or not c.text.strip():
            raise SubmissionError(f"truy vấn {r.qid}: chunk {c.chunk_id} không có text; chạy lại bước truy hồi")
        texts = _pieces(c.text, cfg)
        if expander is not None:
            if any(a <= c.start and c.end <= b for a, b in windows.get(c.uid, ())):
                continue                               # chunk đã nằm trọn trong cửa sổ đã nộp của cùng doc
            w = expander.window(c.uid, c.start, c.end)
            if w is not None and c.text.strip() in w[2]:   # text gốc lệch bản lúc index (doc có ở nhiều shard) thì giữ chunk gốc
                windows.setdefault(c.uid, []).append(w[:2])
                texts = [w[2]]
        for text in texts:
            if (c.doc_id, text) in seen:               # cùng doc_id (vi:7 và zh:7) và cùng nội dung: chỉ nộp một lần
                continue
            seen.add((c.doc_id, text))
            chunks.append(SubChunk(doc_id=c.doc_id, chunk_text=text))
    return SubItem(id=r.qid, relevant_docs=docs, relevant_chunks=chunks[: cfg.max_chunks])


def _pieces(text: str, cfg: BuildCfg) -> list[str]:
    if cfg.split_max_words is None:
        return [text]
    parts = split_text(text, cfg.split_max_words)
    if len(parts) <= 1:
        return [text]
    return ([text] if cfg.keep_full_chunk else []) + parts


def build_items(results: Iterable[QueryResult], cfg: BuildCfg, expander: Expander | None = None) -> list[SubItem]:
    return [build_item(r, cfg, expander) for r in results]