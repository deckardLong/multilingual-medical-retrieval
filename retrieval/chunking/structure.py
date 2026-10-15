# Define structure chunker

from common.schema import Doc, Chunk
from .build import build_chunks
from .merge import merge_short
from .registry import register
from .split import OversizeSplitter
from .units import Piece, body_lines, group_units, assign_parents

# Define structure chunker
@register("structure")
class StructureChunker:
    """Heading -> unit -> merge short -> span parent"""
    def __init__(self, cfg, counter, tag: str):
        self.cfg, self.count, self.tag = cfg, counter, tag
        self.over = OversizeSplitter(cfg.recursive, counter)

    def split(self, doc: Doc) -> list[Chunk]:
        text, sc = doc.text, self.cfg.structure
        lines = body_lines(text)
        if not lines:
            return []
        counts = self.count.count_many([text[s:e] for s, e in lines])
        units = group_units(text, lines, counts, sc.heading_max_chars, sc.target_tokens)
        pieces = merge_short(self._fit(text, units), self.cfg.min_chunk_tokens, sc.hard_tokens)
        if self.cfg.parent.enabled:
            parents = assign_parents(pieces, self.cfg.parent.max_tokens)
        else:
            parents = [(p.start, p.end) for p in pieces]
        return build_chunks(doc, pieces, parents, self.cfg.contextual_prefix, self.tag)

    def _fit(self, text: str, units: list[Piece]) -> list[Piece]:
        out = []
        for u in units:
            if u.tokens <= self.cfg.structure.hard_tokens:
                out.append(u)
                continue
            for a, b in self.over.spans(text, u.start, u.end):
                out.append(Piece(a, b, u.heading, self.count.count(text[a:b]), oversize=True))
        return out