from pathlib import Path
import pyarrow.parquet as pq


def count_rows(path: Path) -> int:
    """Số dòng của một file parquet, đọc từ metadata — không nạp dữ liệu, nên gọi được cho cả trăm file."""
    return pq.ParquetFile(path).metadata.num_rows


def total_rows(paths) -> int:
    """Tổng số dòng của nhiều file; file hỏng hoặc đang ghi dở bị bỏ qua (chỉ dùng làm mẫu số cho thanh tiến độ,
    sai số không được phép làm hỏng vòng chạy)."""
    n = 0
    for p in paths:
        try:
            n += count_rows(p)
        except Exception:                                      # noqa: BLE001
            continue
    return n