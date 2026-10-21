"""Tóm tắt trước khi tải (từ dry run) và sau khi tải (quét đĩa) — để biết sắp tải bao nhiêu và đã có bao nhiêu."""
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Protocol


class _FileInfo(Protocol):          # khớp huggingface_hub.file_download.DryRunFileInfo, không import để khỏi ràng buộc
    filename: str
    file_size: int | None
    will_download: bool


@dataclass(frozen=True)
class PlanSummary:
    n_files: int
    n_to_download: int
    bytes_to_download: int
    by_prefix: dict[str, tuple[int, int]]      # 3 cấp thư mục đầu của đường dẫn trong repo -> (số file, số byte)


def summarize_plan(infos: Iterable[_FileInfo]) -> PlanSummary:
    infos = list(infos)
    by_prefix: dict[str, tuple[int, int]] = {}
    n_dl = bytes_dl = 0
    for f in infos:
        if not f.will_download:
            continue
        n_dl += 1
        size = f.file_size or 0
        bytes_dl += size
        key = "/".join(Path(f.filename).parts[:3])
        n0, b0 = by_prefix.get(key, (0, 0))
        by_prefix[key] = (n0 + 1, b0 + size)
    return PlanSummary(len(infos), n_dl, bytes_dl, dict(sorted(by_prefix.items())))


@dataclass(frozen=True)
class LocalSummary:
    n_shards: dict[str, int]       # tên phân vùng ("a", "b", ...) -> số shard .jsonl(.zst) đang có
    bytes_total: int
    has_links: bool
    has_queries: bool


def scan_local(corpus_dir: Path, queries_path: Path, links_path: Path) -> LocalSummary:
    docs_dir = corpus_dir / "viz" / "docs"
    n_shards: dict[str, int] = {}
    total = 0
    if docs_dir.exists():
        for part_dir in sorted(p for p in docs_dir.iterdir() if p.is_dir()):
            shards = [*part_dir.glob("*.jsonl.zst"), *part_dir.glob("*.jsonl")]
            n_shards[part_dir.name] = len(shards)
            total += sum(s.stat().st_size for s in shards)
    return LocalSummary(n_shards, total, links_path.exists(), queries_path.exists())