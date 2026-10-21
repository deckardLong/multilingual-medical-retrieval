import logging
from dataclasses import dataclass, field
from retrieval.progress import no_bars
from .plan import pending_chunk_jobs
from .shard import chunk_shard

log = logging.getLogger(__name__)


@dataclass
class ChunkSummary:
    done: int = 0
    failed: list[str] = field(default_factory=list)
    n_chunks: int = 0


def chunk_pending(settings, chunker, limit: int | None = None, make_bar=None) -> ChunkSummary:
    """Chunk mọi shard doc còn thiếu. Shard lỗi được ghi nhận, các shard khác vẫn chạy.
    Thanh đếm theo shard: số chunk chỉ biết được sau khi đã chunk, nên không dùng làm mẫu số được."""
    jobs = pending_chunk_jobs(settings.env.r2ai_corpus_dir, settings.chunks_dir)[:limit]
    make_bar = make_bar or no_bars
    out = ChunkSummary()
    with make_bar("chunk", len(jobs), "shard") as bar:
        for j in jobs:
            bar.where(j.docs.name)
            try:
                st = chunk_shard(j.docs, j.chunks, chunker)
            except Exception as e:                      # noqa: BLE001
                log.error("chunk lỗi %s: %s", j.docs.name, e)
                out.failed.append(j.docs.name)
                continue
            finally:
                bar.advance()
            out.done += 1; out.n_chunks += st.n_chunks
            log.info("%s: %d chunk", j.docs.name, st.n_chunks)
    return out