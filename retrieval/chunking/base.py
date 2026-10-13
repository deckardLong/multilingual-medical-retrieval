from typing import Protocol
from common.schema import Doc, Chunk


class Chunker(Protocol):
    def split(self, doc: Doc) -> list[Chunk]: 
        ...