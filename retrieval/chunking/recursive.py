# Define recursive chunker

from common.schema import Doc, Chunk
from .build import build_chunks
from .registry import register
from .split import OversizeSplitter
from .units import Piece, title_end

# Define class
@register("recursive")
class RecursiveChunker:
    def __init__(self, cfg, counter, tag: str):
        self.cfg, self.count, self.tag = cfg, counter, tag
        self.over = OversizeSplitter(cfg.recursive, counter)

    def split(self, doc: Doc) -> list[Chunk]:
        begin = title_end(doc.text)
        if begin == 0:
            return []
        pieces = [Piece(a, b, "", self.count.count(doc.text[a:b]))
                  for a, b in self.over.spans(doc.text, begin, len(doc.text))]
        parents = [(p.start, p.end) for p in pieces]
        return build_chunks(doc, pieces, parents, self.cfg.contextual_prefix, self.tag)