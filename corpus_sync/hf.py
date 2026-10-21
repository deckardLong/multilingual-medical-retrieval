"""Tải kho ngữ liệu từ HuggingFace Hub về một thư mục đệm, rồi xếp lại đúng layout mà retrieval/* cần:
   <staging>/corpus/** → env.r2ai_corpus_dir/** (bỏ tiền tố "corpus/" của repo), <staging>/queries/** → ROOT/queries/**.
   CHỈ CHẠY TRÊN MÁY CÓ MẠNG RA NGOÀI THẬT. Sandbox của Claude không có quyền tới huggingface.co nên không tự chạy
   được ở đây; module này được viết để BẠN chạy, không phải để chạy trong phiên làm việc này."""
import shutil
from pathlib import Path
from huggingface_hub import snapshot_download
from common.config import Env, ROOT
from .settings import SyncCfg

STAGING = ROOT / ".hf_corpus_cache"      # bộ nhớ đệm của huggingface_hub (resume theo ETag); có thể xoá an toàn


def plan(cfg: SyncCfg, env: Env, patterns: list[str] | None = None):
    """Không tải gì cả; trả danh sách file kèm kích thước và việc có thật sự cần tải hay không."""
    return snapshot_download(cfg.repo_id, repo_type=cfg.repo_type, revision=cfg.revision, local_dir=STAGING,
                             allow_patterns=patterns or cfg.allow_patterns, max_workers=cfg.max_workers,
                             token=env.hf_token, dry_run=True)


def fetch(cfg: SyncCfg, env: Env, patterns: list[str] | None = None, queries_dir: Path | None = None) -> None:
    """Tải thật (chỉ phần còn thiếu/đổi), rồi xếp vào đúng chỗ. Không bao giờ xoá file đã có ở đích.
    `queries_dir` mặc định ROOT/"queries" (khớp mặc định của run_queries.py/run_submit.py); tham số hoá để test
    không đụng vào thư mục thật của dự án."""
    snapshot_download(cfg.repo_id, repo_type=cfg.repo_type, revision=cfg.revision, local_dir=STAGING,
                      allow_patterns=patterns or cfg.allow_patterns, max_workers=cfg.max_workers, token=env.hf_token)
    place(STAGING / "corpus", env.r2ai_corpus_dir)
    place(STAGING / "queries", queries_dir or (ROOT / "queries"))


def place(src: Path, dst: Path) -> int:
    """Sao chép (không di chuyển — staging còn giữ lại để lần sau chỉ tải phần mới) mọi file mới hoặc đổi kích
    thước từ `src` sang `dst`, giữ nguyên cấu trúc thư mục con. Trả số file đã sao chép."""
    if not src.exists():
        return 0
    n = 0
    for f in src.rglob("*"):
        if not f.is_file():
            continue
        out = dst / f.relative_to(src)
        if out.exists() and out.stat().st_size == f.stat().st_size:
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, out)
        n += 1
    return n