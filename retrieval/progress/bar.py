"""Thanh tiến độ cho pipeline. Nguyên tắc chống trùng dòng:
   1. MỘT thanh sống tại một thời điểm — mỗi stage mở thanh của mình rồi đóng trước khi stage sau bắt đầu,
      không bao giờ mở thanh con theo từng shard.
   2. Log đi qua tqdm.write (CLI bọc logging_redirect_tqdm) nên dòng log không cắt ngang thanh.
   3. Thanh của thư viện bên dưới (FlagEmbedding...) bị tắt bằng quiet_tqdm trong lúc encode.
Khi đầu ra không phải terminal (ghi log ra file, chạy nền) thanh vẫn chạy nhưng chỉ in lại mỗi 10 giây,
để file log không phình ra hàng nghìn dòng."""
import sys
from typing import Callable, Protocol

TTY_INTERVAL, FILE_INTERVAL = 0.1, 10.0


class ProgressLike(Protocol):
    def advance(self, n: int = 1) -> None: ...
    def where(self, label: str) -> None: ...


class NullProgress:
    """Không hiển thị gì — dùng khi tắt thanh hoặc trong test, để chỗ gọi không phải rải `if bar is not None`."""
    enabled = False

    def __enter__(self): return self
    def __exit__(self, *exc): return False
    def advance(self, n: int = 1) -> None: pass
    def where(self, label: str) -> None: pass


class Progress:
    """Bọc tqdm: thanh chỉ được tạo trong __enter__ (sau khi mọi thanh của thư viện khác đã bị tắt) và luôn
    được đóng trong __exit__, kể cả khi có lỗi — thanh chưa đóng chính là thứ để lại dòng thừa trên màn hình."""

    def __init__(self, desc: str, total: int, unit: str = "it", stream=None):
        self.desc, self.total, self.unit = desc, total, unit
        self.stream = stream if stream is not None else sys.stderr
        self.n, self._bar = 0, None

    @property
    def enabled(self) -> bool:
        return self._bar is not None

    def __enter__(self):
        from tqdm.auto import tqdm
        isatty = bool(getattr(self.stream, "isatty", lambda: False)())
        self._bar = tqdm(total=self.total, desc=self.desc, unit=self.unit, file=self.stream, dynamic_ncols=True,
                         mininterval=TTY_INTERVAL if isatty else FILE_INTERVAL, leave=True, disable=False)
        return self

    def advance(self, n: int = 1) -> None:
        self.n += n
        if self._bar is not None:
            self._bar.update(n)

    def where(self, label: str) -> None:
        """Tên shard đang xử lý — hiện ở đuôi thanh, không tạo dòng mới."""
        if self._bar is not None:
            self._bar.set_postfix_str(label, refresh=False)

    def __exit__(self, *exc):
        if self._bar is not None:
            self._bar.close()
            self._bar = None
        return False


BarFactory = Callable[[str, int, str], ProgressLike]


def no_bars(desc: str, total: int, unit: str = "it") -> NullProgress:
    return NullProgress()


def tqdm_bars(enabled: bool = True) -> BarFactory:
    """Nhà máy tạo thanh cho CLI; enabled=False trả về thanh rỗng (cờ --no-progress)."""
    if not enabled:
        return no_bars

    def make(desc: str, total: int, unit: str = "it"):
        return Progress(desc, total, unit)

    return make