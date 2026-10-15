from dataclasses import dataclass
from pathlib import Path
from .manifest import Manifest, file_fingerprint

@dataclass(frozen=True)
class IndexJob:
    shard: str          # đường dẫn tương đối, khóa trong manifest
    chunks: Path
    vectors: Path
    fp: str

def pending_index_jobs(chunks_dir: Path, vectors_dir: Path, manifest: Manifest, collection: str) -> list[IndexJob]:
    """Shard có đủ chunk + vector mà chưa (hoặc đã đổi so với lần) vào collection này."""
    if not vectors_dir.exists():
        return []
    jobs = []
    for v in sorted(vectors_dir.rglob("*.parquet")):
        rel = v.relative_to(vectors_dir)
        c = chunks_dir / rel
        fp = file_fingerprint(v)
        if c.exists() and not manifest.is_done(collection, rel.as_posix(), fp):
            jobs.append(IndexJob(rel.as_posix(), c, v, fp))
    return jobs