# Overisze => Recursive chunking

from langchain_text_splitters import RecursiveCharacterTextSplitter

# Define class
class OversizeSplitter:

    def __init__(self, cfg, counter):
        self.sp = RecursiveCharacterTextSplitter(
            chunk_size=cfg.chunk_size, chunk_overlap=cfg.chunk_overlap,
            separators=cfg.separators, length_function=counter.count,
            keep_separator=True, strip_whitespace=True)

    def spans(self, text: str, start: int, end: int) -> list[tuple[int, int]]:
        base, out, cursor = text[start:end], [], 0
        for part in self.sp.split_text(base):
            i = base.find(part, cursor)
            if i < 0:
                raise ValueError("không định vị được mảnh trong văn bản gốc")
            out.append((start + i, start + i + len(part)))
            cursor = i + 1                  # after piece starts by prev piece (overlap)
        return out