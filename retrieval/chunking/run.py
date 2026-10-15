import logging
from dataclasses import dataclass, field
from .plan import pending_chunk_jobs
from .shard import chunk_shard

log = logging.getLogger(__name__)


@dataclass
class ChunkSummary:
    done: int = 0
    failed: list[str] = field(default_factory=list)
    n_chunks: int = 0


def chunk_pending(settings, chunker, limit: int | None = None) -> ChunkSummary:
    """Chunk mọi shard doc còn thiếu. Shard lỗi được ghi nhận, các shard khác vẫn chạy."""
    out = ChunkSummary()
    for j in pending_chunk_jobs(settings.env.r2ai_corpus_dir, settings.chunks_dir)[:limit]:
        try:
            st = chunk_shard(j.docs, j.chunks, chunker)
        except Exception as e:                      # noqa: BLE001
            log.error("chunk lỗi %s: %s", j.docs.name, e)
            out.failed.append(j.docs.name)
            continue
        out.done += 1; out.n_chunks += st.n_chunks
        log.info("%s: %d chunk", j.docs.name, st.n_chunks)
    return out