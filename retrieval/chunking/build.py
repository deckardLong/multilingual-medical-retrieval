# Build chunks

from common.schema import Doc, Chunk
from .context import make_ctx
from .units import Piece

def build_chunks(doc: Doc, pieces: list[Piece], parents: list[tuple[int, int]],
                 contextual_prefix: bool, tag: str) -> list[Chunk]:
    return [
        Chunk(chunk_id=f"{doc.uid}#{n}", uid=doc.uid, doc_id=doc.doc_id, lang=doc.lang,
              start=p.start, end=p.end, p_start=ps, p_end=pe, heading=p.heading,
              ctx=make_ctx(contextual_prefix, doc.title, p.heading),
              text=doc.text[p.start:p.end], n_tokens=p.tokens, chunker_ver=tag)
        for n, (p, (ps, pe)) in enumerate(zip(pieces, parents))
    ]