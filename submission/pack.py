"""Ghi file .json và nén .zip đúng quy định BTC: zip chỉ chứa MỘT file, nằm ở gốc (không thư mục con)."""
import hashlib, os, zipfile
from pathlib import Path
from .schema import SUBMISSION, SubItem


def write_json(items: list[SubItem], path: Path) -> Path:
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(SUBMISSION.dump_json(items))          # UTF-8, giữ nguyên chữ có dấu / chữ Hán
    os.replace(tmp, path)
    return path


def make_zip(json_path: Path, zip_path: Path, arcname: str) -> Path:
    zip_path = Path(zip_path); zip_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = zip_path.with_suffix(zip_path.suffix + ".tmp")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(json_path, arcname=arcname)
    os.replace(tmp, zip_path)
    return zip_path


def read_zip(zip_path: Path) -> list[SubItem]:
    """Mở lại đúng file sẽ đem nộp và kiểm tra nó theo đặc tả; lỗi nếu zip sai quy định hoặc JSON sai cấu trúc."""
    with zipfile.ZipFile(zip_path) as z:
        names = z.namelist()
        if len(names) != 1 or "/" in names[0] or "\\" in names[0]:
            raise ValueError(f"{zip_path}: zip phải chứa đúng một file ở gốc, hiện có {names}")
        return SUBMISSION.validate_json(z.read(names[0]))


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()