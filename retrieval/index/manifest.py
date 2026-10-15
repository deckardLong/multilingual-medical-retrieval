import json, os, time
from pathlib import Path


def file_fingerprint(path: Path) -> str:
    """Shard là file bất biến ghi nguyên tử → (kích thước, mtime) đủ để nhận ra file đổi, mà không phải đọc cả file."""
    st = Path(path).stat()
    return f"{st.st_size}:{st.st_mtime_ns}"


class Manifest:
    """Sổ ghi shard nào đã vào collection nào (JSONL, chỉ ghi thêm). Dòng cuối ghi dở do sập máy sẽ bị bỏ qua."""

    def __init__(self, path: Path):
        self.path, self._done = Path(path), {}
        if self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                try:
                    r = json.loads(line)
                    self._done[(r["collection"], r["shard"])] = r["fp"]
                except (ValueError, KeyError):
                    continue

    def is_done(self, collection: str, shard: str, fp: str) -> bool:
        return self._done.get((collection, shard)) == fp

    def record(self, collection: str, shard: str, fp: str, n_points: int) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        row = dict(collection=collection, shard=shard, fp=fp, n=n_points, ts=time.time())
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n"); f.flush(); os.fsync(f.fileno())
        self._done[(collection, shard)] = fp

    def count(self, collection: str) -> int:
        return sum(1 for (c, _) in self._done if c == collection)