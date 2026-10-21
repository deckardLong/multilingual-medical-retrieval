"""Đọc bảng nhỏ (danh sách truy vấn, danh sách id của BTC) theo đuôi file: .jsonl/.ndjson hoặc parquet."""
import json
from pathlib import Path

import pyarrow.parquet as pq

JSONL_SUFFIXES = frozenset({".jsonl", ".ndjson"})


def read_table(path: Path, wanted: list[str] | None = None, limit: int | None = None) -> tuple[list[str], dict[str, list]]:
    """Trả (tên mọi cột có trong file, {cột: giá trị}) — chỉ nạp các cột `wanted` (có mặt trong file), tối đa `limit` dòng.
    Với JSONL, cột vắng ở một dòng nào đó nhận giá trị None (để chỗ gọi báo lỗi dòng cụ thể)."""
    path = Path(path)
    if path.suffix.lower() in JSONL_SUFFIXES:
        return _read_jsonl(path, wanted, limit)
    names = pq.read_schema(path).names
    keep = names if wanted is None else [c for c in wanted if c in names]
    table = pq.read_table(path, columns=keep)
    return names, {c: table.column(c).to_pylist()[:limit] for c in keep}


def _read_jsonl(path: Path, wanted: list[str] | None, limit: int | None) -> tuple[list[str], dict[str, list]]:
    names: dict[str, None] = {}
    rows: list[dict] = []
    with open(path, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            if not line.strip():
                continue
            full = limit is not None and len(rows) >= limit
            if full and names:
                break
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError(f"{path}: dòng {n} không phải một object JSON")
            names.update(dict.fromkeys(row))
            if not full:                       # limit=0 vẫn đọc dòng đầu để biết tên cột (giống parquet)
                rows.append(row)
    keep = list(names) if wanted is None else [c for c in wanted if c in names]
    return list(names), {c: [r.get(c) for r in rows] for c in keep}