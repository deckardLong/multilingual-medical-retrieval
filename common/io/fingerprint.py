from pathlib import Path


def file_fingerprint(path: Path) -> str:
    """Shard là file bất biến ghi nguyên tử → (kích thước, mtime) đủ để nhận ra file đổi, mà không phải đọc cả file."""
    st = Path(path).stat()
    return f"{st.st_size}:{st.st_mtime_ns}"