"""python -m retrieval.promote [--min-points N]"""
import argparse
from common.config import Env
from retrieval.settings import load_all
from retrieval.index import make_client, promote


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-points", type=int, default=1)
    a = ap.parse_args()
    s = load_all(Env())
    old = promote(make_client(s.env), s.collection, s.index.alias, min_points=a.min_points)
    print(f"{s.index.alias}: {old or '(chưa có)'} -> {s.collection}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())