from pathlib import Path
import pyarrow.parquet as pq
from .types import Query


def load_queries(path: Path, id_col: str = "id", text_col: str = "query", limit: int | None = None) -> list[Query]:
    t = pq.read_table(path)
    for c in (id_col, text_col):
        if c not in t.column_names:
            raise ValueError(f"{path} không có cột '{c}' (có: {t.column_names}); dùng --id-col/--text-col")
    ids, texts = t.column(id_col).to_pylist(), t.column(text_col).to_pylist()
    qs = [Query(qid=int(i), text=str(x)) for i, x in zip(ids, texts)]
    return qs[:limit]