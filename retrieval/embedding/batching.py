from typing import Callable, Iterator, TypeVar

T = TypeVar("T")

def slices(n: int, size: int, start: int = 0) -> Iterator[tuple[int, int]]:
    """(a, b) nửa mở chia n phần tử thành các lát tối đa `size`, bắt đầu từ phần tử `start`
    (resume: phần trước `start` đã mã hoá xong từ lần chạy trước)."""
    if size <= 0:
        raise ValueError("size phải > 0")
    if start < 0:
        raise ValueError("start không được âm")
    for a in range(start, n, size):
        yield a, min(a + size, n)

def is_oom(e: BaseException) -> bool:
    return "out of memory" in str(e).lower()

def with_oom_backoff(fn: Callable[[int], T], batch_size: int, min_batch: int = 1,
                     on_oom: Callable[[int], None] | None = None) -> tuple[T, int]:
    """Chạy fn(batch_size); hết VRAM thì giảm một nửa rồi thử lại. Trả (kết quả, batch_size đã dùng)
    để các lần gọi sau không lặp lại lần thất bại."""
    bs = batch_size
    while True:
        try:
            return fn(bs), bs
        except Exception as e:
            if not is_oom(e) or bs <= min_batch:
                raise
            bs = max(min_batch, bs // 2)
            if on_oom:
                on_oom(bs)