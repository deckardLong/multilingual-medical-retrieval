"""Resume giữa chừng MỘT shard. Mỗi lát vừa mã hoá xong được ghi ngay thành một 'part' trong thư mục
<vector>.parts/; chạy lại sau khi gián đoạn (Ctrl-C, mất điện, máy hết hạn thuê) thì bỏ qua phần đã làm.
Part được ghi nguyên tử và chỉ được tính khi đọc lại được, nên part ghi dở lúc sập máy sẽ bị làm lại chứ
không bao giờ lọt vào kết quả."""
import json
import shutil
from pathlib import Path

import numpy as np
from common.io import count_rows, merge_vector_parts, write_vectors
from common.schema import SparseVec

META = "meta.json"
PART_SUFFIX = ".parquet"


def parts_dir(out_path: Path) -> Path:
    return Path(out_path).with_name(Path(out_path).name + ".parts")


def _valid_parts(d: Path) -> tuple[list[Path], int]:
    """Các part liên tiếp đọc được, kể từ part đầu, kèm tổng số dòng. Gặp part hỏng thì dừng ở đó: mọi part
    sau nó bị bỏ (thứ tự phải liền mạch thì mới ghép lại đúng thứ tự chunk ban đầu)."""
    parts, n = [], 0
    for p in sorted(d.glob(f"*{PART_SUFFIX}")):
        try:
            rows = count_rows(p)
        except Exception:                                   # noqa: BLE001 — part hỏng: coi như chưa làm
            break
        parts.append(p)
        n += rows
    return parts, n


class Checkpoint:
    """Sổ tiến độ của một shard. `done` = số chunk đã mã hoá xong và ghi an toàn."""

    def __init__(self, dir: Path, parts: list[Path], done: int):
        self.dir, self.parts, self.done = dir, parts, done

    @property
    def resumed(self) -> bool:
        return self.done > 0

    def write_part(self, ids: list[str], dense: np.ndarray, sparse: list[SparseVec]) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        p = self.dir / f"{len(self.parts):05d}{PART_SUFFIX}"
        write_vectors(p, ids, dense, sparse)                # đã ghi nguyên tử (tmp rồi đổi tên)
        self.parts.append(p)
        self.done += len(ids)

    def merge_into(self, out_path: Path, dim: int) -> int:
        """Gộp mọi part thành file vector cuối cùng rồi xoá thư mục part. Shard rỗng vẫn phải có file (để
        stage sau biết shard này đã xong), nên ghi file rỗng đúng schema."""
        if self.parts:
            n = merge_vector_parts(self.parts, out_path)
        else:
            write_vectors(out_path, [], np.zeros((0, dim), np.float16), [])
            n = 0
        self.discard()
        return n

    def discard(self) -> None:
        shutil.rmtree(self.dir, ignore_errors=True)


def open_checkpoint(out_path: Path, source_fp: str, n_total: int) -> Checkpoint:
    """Mở (hoặc tạo) sổ tiến độ cho shard. Nếu file chunk nguồn đã khác so với lần chạy trước — hoặc số chunk
    đổi — thì phần làm dở không còn khớp nữa: bỏ hết và làm lại từ đầu."""
    d = parts_dir(out_path)
    want = {"source_fp": source_fp, "n_total": n_total}
    meta_path = d / META
    if d.exists():
        try:
            got = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            got = None
        if got != want:
            shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True, exist_ok=True)
    meta_path.write_text(json.dumps(want), encoding="utf-8")
    parts, done = _valid_parts(d)
    if done > n_total:                                      # part nhiều hơn cả shard: dữ liệu lạ, làm lại cho chắc
        shutil.rmtree(d, ignore_errors=True)
        d.mkdir(parents=True, exist_ok=True)
        meta_path.write_text(json.dumps(want), encoding="utf-8")
        parts, done = [], 0
    for stale in sorted(d.glob(f"*{PART_SUFFIX}"))[len(parts):]:
        stale.unlink(missing_ok=True)                       # part sau một part hỏng: không dùng được nữa
    return Checkpoint(d, parts, done)