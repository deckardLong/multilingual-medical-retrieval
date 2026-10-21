"""Kiểm tra doc_id với danh sách id của BTC. Tài liệu tiếng Anh dùng PMID nên không nằm trong danh sách đó."""
from typing import Iterable
from retrieval.results import QueryResult
from .problems import Problem, sample

BTC_LANGS = frozenset({"vi", "zh"})


def check_ids(results: Iterable[QueryResult], known_ids: set[str] | None) -> list[Problem]:
    if known_ids is None:
        return [Problem("warning", "không có danh sách id của BTC nên bỏ qua việc kiểm tra doc_id tiếng Việt/Trung")]
    out: list[Problem] = []
    for r in results:
        unknown = sorted({c.doc_id for c in r.candidates if c.uid.split(":", 1)[0] in BTC_LANGS and c.doc_id not in known_ids})
        if unknown:
            out.append(Problem("error", f"{len(unknown)} doc_id không thuộc danh sách của BTC: {sample(unknown)}", r.qid))
    return out