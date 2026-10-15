from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class ShardJob:
    chunks: Path
    vectors: Path

def pending_jobs(chunks_dir: Path, vectors_dir: Path) -> list[ShardJob]:
    """Shard chunk chưa có file vector. vectors_dir mang embed_tag (có hash cấu hình) và file ghi nguyên tử,
    nên 'file tồn tại' nghĩa là đã embed xong với đúng cấu hình này."""
    if not chunks_dir.exists():
        return []
    jobs = []
    for src in sorted(chunks_dir.rglob("*.parquet")):
        dst = vectors_dir / src.relative_to(chunks_dir)
        if not dst.exists():
            jobs.append(ShardJob(src, dst))
    return jobs