from dataclasses import dataclass
from retrieval.chunking import chunk_pending, pending_chunk_jobs, ChunkSummary
from retrieval.embedding import embed_pending, pending_jobs, RunSummary
from retrieval.index import index_pending, IndexSummary

@dataclass
class CycleReport:
    chunk: ChunkSummary
    embed: RunSummary
    index: IndexSummary

    @property
    def idle(self) -> bool:
        return not (self.chunk.done or self.embed.done or self.index.done)

    @property
    def failed(self) -> list[str]:
        return [*self.chunk.failed, *self.embed.failed, *self.index.failed]


def run_cycle(settings, client, manifest, chunker_factory, embedder_factory, limit: int | None = None,
              make_bar=None) -> CycleReport:
    """Một vòng: doc mới → chunk → embed → upsert. Model chỉ được tải khi thật sự có việc.
    `make_bar` tạo thanh tiến độ cho từng stage (mặc định: không hiện gì)."""
    if pending_chunk_jobs(settings.env.r2ai_corpus_dir, settings.chunks_dir):
        ck = chunk_pending(settings, chunker_factory(), limit, make_bar)
    else:
        ck = ChunkSummary()
    if pending_jobs(settings.chunks_dir, settings.vectors_dir):
        em = embed_pending(settings, embedder_factory(), limit, make_bar)
    else:
        em = RunSummary(0, [], 0, 0.0)
    return CycleReport(ck, em, index_pending(settings, client, manifest, limit, make_bar))