from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ChunkJob:
    docs: Path
    chunks: Path


def _stem(p: Path) -> str:
    n = p.name
    for suf in (".jsonl.zst", ".jsonl"):
        if n.endswith(suf):
            return n[: -len(suf)]
    return p.stem


def pending_chunk_jobs(corpus_dir: Path, chunks_dir: Path) -> list[ChunkJob]:
    """Shard doc chưa có shard chunk. Thư mục chunks_dir mang chunk_tag (có hash cấu hình), file ghi nguyên tử."""
    if not corpus_dir.exists():
        return []
    jobs = []
    for p in sorted([*corpus_dir.rglob("*.jsonl.zst"), *corpus_dir.rglob("*.jsonl")]):
        rel = p.relative_to(corpus_dir)
        out = chunks_dir / rel.parent / (_stem(p) + ".parquet")
        if not out.exists():
            jobs.append(ChunkJob(p, out))
    return jobs