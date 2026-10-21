from pathlib import Path
from common.io.tables import read_table


def load_id_set(path: Path) -> set[str]:
    """Tập id của BTC (JSONL {"id","url"} hoặc parquet), dạng chuỗi như doc_id trong bài nộp."""
    names, cols = read_table(path, wanted=["id"])
    if "id" not in names:
        raise ValueError(f"{path} không có cột 'id' (có: {names})")
    return {str(i) for i in cols["id"] if i is not None}