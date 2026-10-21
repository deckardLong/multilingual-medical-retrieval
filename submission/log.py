"""Nhật ký các lần nộp (mỗi ngày tối đa 10 lần ở public, 5 lần tổng ở private): một dòng CSV cho mỗi lần dựng bài nộp."""
import csv
from pathlib import Path

FIELDS = ["time", "zip", "sha256", "n_queries", "docs_total", "chunks_total", "queries_without_docs", "note", "public_score"]


def append_log(path: Path, row: dict) -> None:
    """public_score để trống: điền tay sau khi có điểm trên bảng xếp hạng."""
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.exists() or path.stat().st_size == 0
    with open(path, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        w.writerow({k: row.get(k, "") for k in FIELDS})