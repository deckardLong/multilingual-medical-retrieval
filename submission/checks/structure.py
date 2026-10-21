"""Kiểm tra bài nộp đã dựng xong theo đặc tả của BTC (bài thiếu câu hoặc sai định dạng sẽ không được chấm)."""
import re
from collections import Counter
from typing import Iterable
from retrieval.chunking.tokens import TokenCounter
from ..schema import SubItem
from .problems import Problem, sample

_DIGITS = re.compile(r"[0-9]+")


def check_items(items: Iterable[SubItem], expected_qids: set[int] | None, max_chunk_tokens: int,
                counter: TokenCounter) -> list[Problem]:
    items = list(items)
    out: list[Problem] = []
    got = [i.id for i in items]
    dup = sorted(q for q, n in Counter(got).items() if n > 1)
    if dup:
        out.append(Problem("error", f"id truy vấn bị lặp: {sample(dup)}"))
    if expected_qids is not None:
        missing, extra = sorted(expected_qids - set(got)), sorted(set(got) - expected_qids)
        if missing:
            out.append(Problem("error", f"thiếu {len(missing)} truy vấn (bài thiếu câu sẽ không được chấm): {sample(missing)}"))
        if extra:
            out.append(Problem("error", f"{len(extra)} id không có trong tập truy vấn: {sample(extra)}"))
    for it in items:
        out += _check_item(it, max_chunk_tokens, counter)
    return out


def _check_item(it: SubItem, max_tokens: int, counter: TokenCounter) -> list[Problem]:
    out: list[Problem] = []
    bad_ids = [d for d in it.relevant_docs + [c.doc_id for c in it.relevant_chunks] if not _DIGITS.fullmatch(d)]
    if bad_ids:
        out.append(Problem("error", f"doc_id phải là chuỗi chữ số (id của BTC hoặc PMID): {sample(sorted(set(bad_ids)))}", it.id))
    if len(set(it.relevant_docs)) != len(it.relevant_docs):
        out.append(Problem("error", "relevant_docs có doc_id lặp", it.id))
    blank = sum(1 for c in it.relevant_chunks if not c.chunk_text.strip())
    if blank:
        out.append(Problem("error", f"{blank} chunk_text rỗng", it.id))
    orphan = {c.doc_id for c in it.relevant_chunks} - set(it.relevant_docs)
    if orphan:
        out.append(Problem("warning", f"chunk thuộc doc không có trong relevant_docs: {sample(sorted(orphan))}", it.id))
    if it.relevant_chunks:
        too_long = sum(1 for n in counter.count_many([c.chunk_text for c in it.relevant_chunks]) if n > max_tokens)
        if too_long:
            out.append(Problem("warning", f"{too_long} chunk_text dài hơn ~{max_tokens} token (BTC chỉ khuyến nghị)", it.id))
    if not it.relevant_docs and not it.relevant_chunks:
        out.append(Problem("warning", "không có kết quả nào cho truy vấn này", it.id))
    return out