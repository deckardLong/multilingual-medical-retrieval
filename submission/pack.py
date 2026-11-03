"""Ghi file .json và nén .zip đúng quy định BTC: zip chỉ chứa MỘT file, nằm ở gốc (không thư mục con)."""
import hashlib, json, os, zipfile
from pathlib import Path
from .schema import SUBMISSION, SubItem


def _wire(items: list[SubItem], int_doc_ids: bool) -> list[dict]:
    """Dạng ghi ra file. int_doc_ids=True: doc_id viết dạng số (196977) thay vì chuỗi ("196977")."""
    data = SUBMISSION.dump_python(items, mode="json")
    if int_doc_ids:
        for it in data:
            it["relevant_docs"] = [int(d) for d in it["relevant_docs"]]
            for c in it["relevant_chunks"]:
                c["doc_id"] = int(c["doc_id"])
    return data


def write_json(items: list[SubItem], path: Path, int_doc_ids: bool = False) -> Path:
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    text = json.dumps(_wire(items, int_doc_ids), ensure_ascii=False, indent=2)   # giữ nguyên chữ có dấu / chữ Hán
    tmp.write_bytes(text.encode("utf-8"))
    os.replace(tmp, path)
    return path


def _ids_to_str(data):
    """doc_id dạng số (bool không tính) → chuỗi, để kiểm tra lại bằng cùng schema với bản chuỗi."""
    if not isinstance(data, list):
        return data
    as_str = lambda v: str(v) if isinstance(v, int) and not isinstance(v, bool) else v
    for it in data:
        if isinstance(it, dict):
            if isinstance(it.get("relevant_docs"), list):
                it["relevant_docs"] = [as_str(d) for d in it["relevant_docs"]]
            for c in it.get("relevant_chunks") or []:
                if isinstance(c, dict) and "doc_id" in c:
                    c["doc_id"] = as_str(c["doc_id"])
    return data


def make_zip(json_path: Path, zip_path: Path, arcname: str) -> Path:
    zip_path = Path(zip_path); zip_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = zip_path.with_suffix(zip_path.suffix + ".tmp")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        z.write(json_path, arcname=arcname)
    os.replace(tmp, zip_path)
    return zip_path


def read_zip(zip_path: Path) -> list[SubItem]:
    """Mở lại đúng file sẽ đem nộp và kiểm tra nó theo đặc tả; lỗi nếu zip sai quy định hoặc JSON sai cấu trúc."""
    with zipfile.ZipFile(zip_path) as z:
        names = z.namelist()
        if len(names) != 1 or "/" in names[0] or "\\" in names[0]:
            raise ValueError(f"{zip_path}: zip phải chứa đúng một file ở gốc, hiện có {names}")
        return SUBMISSION.validate_python(_ids_to_str(json.loads(z.read(names[0]))))


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()