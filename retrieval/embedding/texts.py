# Chunk texts

from retrieval.chunking.context import embed_text

# Add context into chunk
def chunk_texts(ctxs: list[str], texts: list[str]) -> list[str]:
    return [embed_text(c, t) for c, t in zip(ctxs, texts)]