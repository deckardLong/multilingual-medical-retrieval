import json, os
from pathlib import Path
from typing import Iterable, Iterator
from .types import QueryResult


def write_results(path: Path, results: Iterable[QueryResult]) -> int:
    """JSONL, mỗi dòng một truy vấn; ghi nguyên tử. Trả số dòng."""
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    tmp, n = path.with_suffix(path.suffix + ".tmp"), 0
    with open(tmp, "w", encoding="utf-8") as f:
        for r in results:
            f.write(r.model_dump_json() + "\n"); n += 1
    os.replace(tmp, path)
    return n


def read_results(path: Path) -> Iterator[QueryResult]:
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield QueryResult.model_validate_json(line)


def write_json(path: Path, obj: dict) -> None:
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)