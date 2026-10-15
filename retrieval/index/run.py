import logging
from dataclasses import dataclass, field
from .collection import ensure_collection
from .manifest import Manifest
from .plan import pending_index_jobs
from .upsert import upsert_shard

log = logging.getLogger(__name__)


@dataclass
class IndexSummary:
    done: int = 0
    failed: list[str] = field(default_factory=list)
    n_points: int = 0


def index_pending(settings, client, manifest: Manifest, limit: int | None = None) -> IndexSummary:
    """Đưa mọi shard còn thiếu vào collection hiện hành. Shard lỗi được ghi nhận, các shard khác vẫn chạy."""
    jobs = pending_index_jobs(settings.chunks_dir, settings.vectors_dir, manifest, settings.collection)[:limit]
    out = IndexSummary()
    if not jobs:
        return out
    ensure_collection(client, settings.collection, settings.index, settings.embed)
    for j in jobs:
        try:
            st = upsert_shard(client, settings.collection, j.chunks, j.vectors, settings.index,
                              use_sparse=settings.embed.use_sparse)
        except Exception as e:                      # noqa: BLE001
            log.error("index lỗi %s: %s", j.shard, e)
            out.failed.append(j.shard)
            continue
        manifest.record(settings.collection, j.shard, j.fp, st.n_points)
        out.done += 1; out.n_points += st.n_points
        log.info("%s: %d điểm", j.shard, st.n_points)
    return out