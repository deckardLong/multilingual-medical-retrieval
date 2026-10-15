"""python -m retrieval.run_select --pool candidates/<run_id>.pool.jsonl"""
import argparse
from pathlib import Path
from common.config import Env, ROOT
from retrieval.settings import load_all
from retrieval.search.runner import run_select


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pool", required=True)
    ap.add_argument("--out-dir", default=str(ROOT / "candidates"))
    a = ap.parse_args()
    res = run_select(load_all(Env()), Path(a.pool), Path(a.out_dir))
    print(f"{res['run_id']} → {res['out']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())