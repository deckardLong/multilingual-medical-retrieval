"""Kiểm tra doc_id với danh sách id của BTC (gồm cả tài liệu PubMed tiếng Anh, cũng dùng id trong file links)."""
from typing import Iterable
from retrieval.results import QueryResult
from .problems import Problem, sample


def check_ids(results: Iterable[QueryResult], known_ids: set[str] | None) -> list[Problem]:
    if known_ids is None:
        return [Problem("warning", "không có danh sách id của BTC nên bỏ qua việc kiểm tra doc_id")]
    out: list[Problem] = []
    for r in results:
        unknown = sorted({c.doc_id for c in r.candidates if c.doc_id not in known_ids})
        if unknown:
            out.append(Problem("error", f"{len(unknown)} doc_id không thuộc danh sách của BTC: {sample(unknown)}", r.qid))
    return out