"""Phát hiện GPU bị driver kìm xung trong lúc mã hoá (laptop ở chế độ Silent/Eco, rút sạc, quá nhiệt) để cảnh báo,
thay vì lặng lẽ chạy chậm hơn cả chục lần. Không có nvidia-smi thì không làm gì."""
import logging
import subprocess
import time

log = logging.getLogger(__name__)

QUERY = ("clocks.sm,clocks.max.sm,power.draw,temperature.gpu,"
         "clocks_throttle_reasons.sw_power_cap,clocks_throttle_reasons.sw_thermal_slowdown,"
         "clocks_throttle_reasons.hw_slowdown")
WARN_EVERY_SECONDS = 600
SLOW_CLOCK_RATIO = 0.25


def read_gpu() -> dict | None:
    try:
        out = subprocess.run(["nvidia-smi", f"--query-gpu={QUERY}", "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, timeout=5).stdout.strip().splitlines()
    except (OSError, subprocess.SubprocessError):
        return None
    if not out:
        return None
    f = [x.strip() for x in out[0].split(",")]
    try:
        return dict(sm=float(f[0]), sm_max=float(f[1]), watts=float(f[2]), temp=float(f[3]),
                    power_cap=f[4] == "Active", thermal=f[5] == "Active", hw_slow=f[6] == "Active")
    except (ValueError, IndexError):
        return None


def throttle_reason(g: dict) -> str | None:
    if g["sm_max"] <= 0 or g["sm"] >= SLOW_CLOCK_RATIO * g["sm_max"]:
        return None
    causes = [name for name, on in (("giới hạn công suất", g["power_cap"]), ("quá nhiệt", g["thermal"]),
                                    ("phần cứng hạ xung", g["hw_slow"])) if on]
    return ", ".join(causes) or None


class GpuWatch:
    def __init__(self, read=read_gpu, clock=time.monotonic):
        self.read, self.clock, self.last_warn = read, clock, None

    def after_slice(self, n_chunks: int, seconds: float) -> str | None:
        """Gọi ngay sau mỗi lát (GPU vừa chạy xong). Trả nội dung cảnh báo nếu vừa cảnh báo."""
        g = self.read()
        if g is None:
            return None
        reason = throttle_reason(g)
        now = self.clock()
        if reason is None or (self.last_warn is not None and now - self.last_warn < WARN_EVERY_SECONDS):
            return None
        self.last_warn = now
        msg = (f"GPU đang bị kìm xung ({reason}): SM {g['sm']:.0f}/{g['sm_max']:.0f} MHz, {g['watts']:.0f} W, "
               f"{g['temp']:.0f}°C → lát vừa rồi {n_chunks / max(seconds, 1e-9):.1f} chunk/giây. "
               "Cắm sạc và chuyển Armoury Crate sang chế độ Performance/Turbo (Silent/Eco giới hạn công suất GPU).")
        log.warning(msg)
        return msg
