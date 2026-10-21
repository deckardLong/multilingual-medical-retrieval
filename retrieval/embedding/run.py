import logging
from dataclasses import dataclass
from common.io import total_rows
from retrieval.progress import no_bars
from .encode_shard import encode_shard
from .plan import pending_jobs
from .stats import EncodeStats

log = logging.getLogger(__name__)

@dataclass
class RunSummary:
    done: int
    failed: list[str]
    n_chunks: int
    seconds: float

    @property
    def chunks_per_s(self) -> float:
        return self.n_chunks / self.seconds if self.seconds > 0 else 0.0

def embed_pending(settings, embedder, limit: int | None = None, make_bar=None) -> RunSummary:
    """Embed mọi shard chunk còn thiếu vector. Một shard lỗi thì ghi nhận rồi làm tiếp shard khác.
    Một thanh tiến độ duy nhất cho cả lượt, đếm theo chunk (mẫu số lấy từ metadata parquet, không đọc dữ liệu)."""
    jobs = pending_jobs(settings.chunks_dir, settings.vectors_dir)[:limit]
    make_bar = make_bar or no_bars
    done, failed, n, secs = 0, [], 0, 0.0
    with make_bar("embed", total_rows(j.chunks for j in jobs), "chunk") as bar:
        for j in jobs:
            bar.where(j.chunks.name)
            try:
                st: EncodeStats = encode_shard(j.chunks, j.vectors, embedder, settings.embed,
                                               on_progress=bar.advance)
            except Exception as e:                      # noqa: BLE001 — shard khác vẫn phải chạy tiếp
                log.error("embed lỗi %s: %s", j.chunks.name, e)
                failed.append(j.chunks.name)
                continue
            done += 1; n += st.n_chunks; secs += st.seconds
            log.info("%s: %d chunk, %.0f chunk/s", j.chunks.name, st.n_chunks, st.chunks_per_s)
    return RunSummary(done, failed, n, secs)