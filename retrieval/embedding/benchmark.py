import time

def measure_speed(embedder, texts: list[str], batch_size: int | None = None) -> float:
    """chunk/giây (một lượt khởi động bỏ ra ngoài số đo)."""
    embedder.encode_docs(texts[:1])
    t0 = time.perf_counter()
    embedder.encode_docs(texts)
    dt = time.perf_counter() - t0
    return len(texts) / dt if dt > 0 else float("inf")