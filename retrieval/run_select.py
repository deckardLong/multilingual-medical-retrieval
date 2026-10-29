"""python -m retrieval.run_select [--pool candidates/<run_id>.pool.jsonl] [--no-progress]"""
import argparse
from pathlib import Path
from common.config import Env, ROOT
from retrieval.progress import log_redirect, tqdm_bars
from retrieval.settings import load_all
from retrieval.search.runner import latest_pool, run_select


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pool", default=None, help="mặc định: file *.pool.jsonl mới nhất trong --out-dir")
    ap.add_argument("--out-dir", default=str(ROOT / "candidates"))
    ap.add_argument("--no-progress", action="store_true", help="không hiện thanh tiến độ")
    a = ap.parse_args()
    show = not a.no_progress
    pool = Path(a.pool) if a.pool else latest_pool(Path(a.out_dir))
    print(f"pool: {pool}")
    with log_redirect(show):
        res = run_select(load_all(Env()), pool, Path(a.out_dir), tqdm_bars(show))
    print(f"{res['run_id']} → {res['out']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
