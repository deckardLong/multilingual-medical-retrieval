from pathlib import Path
from common.io.tables import read_table
from .types import Query


def load_queries(path: Path, id_col: str = "id", text_col: str = "query", limit: int | None = None) -> list[Query]:
    """Đọc truy vấn từ JSONL (định dạng BTC phát: {"id": int, "query": str}) hoặc parquet."""
    names, cols = read_table(path, wanted=[id_col, text_col], limit=limit)
    for c in (id_col, text_col):
        if c not in names:
            raise ValueError(f"{path} không có cột '{c}' (có: {names}); dùng --id-col/--text-col")
    qs = []
    for row, (i, x) in enumerate(zip(cols[id_col], cols[text_col])):
        if i is None or x is None or not str(x).strip():
            raise ValueError(f"{path}: dòng {row} có '{id_col}' hoặc '{text_col}' rỗng")       # không để "None" thành truy vấn
        qs.append(Query(qid=int(i), text=str(x)))
    return qs