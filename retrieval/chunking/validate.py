# Validate docs

from common.schema import Doc, Chunk
from .units import title_end

# Validate doc chunks
def validate_doc_chunks(doc: Doc, chunks: list[Chunk]) -> list[str]:
    """Chunk from original docs"""
    errs, n, prev = [], len(doc.text), -1
    for c in chunks:
        if not (0 <= c.start < c.end <= n):
            errs.append(f"{c.chunk_id}: offset ngoài phạm vi")
            continue
        if doc.text[c.start:c.end] != c.text:
            errs.append(f"{c.chunk_id}: text khác doc.text[start:end]")
        if not c.text.strip():
            errs.append(f"{c.chunk_id}: chunk rỗng")
        if not (0 <= c.p_start <= c.start and c.end <= c.p_end <= n):
            errs.append(f"{c.chunk_id}: span cha không bao span con")
        if c.start < prev:
            errs.append(f"{c.chunk_id}: thứ tự offset lùi")
        prev = c.start
    return errs

# Coverage
def coverage(doc: Doc, chunks: list[Chunk]) -> float:
    mark = bytearray(len(doc.text))
    for c in chunks:
        mark[c.start:c.end] = b"\x01" * (c.end - c.start)
    body = range(title_end(doc.text), len(doc.text))
    total = sum(1 for i in body if not doc.text[i].isspace())
    hit = sum(1 for i in body if mark[i] and not doc.text[i].isspace())
    return hit / total if total else 1.0