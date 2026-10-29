"""python -m retrieval.run_queries [--queries queries/query.parquet] [--limit N] [--live]"""
import argparse, logging
from pathlib import Path
from common.config import Env, ROOT
from retrieval.settings import load_all
from retrieval.embedding import build_embedder
from retrieval.rerank import build_reranker
from retrieval.index import make_client
from retrieval.progress import log_redirect, tqdm_bars
from retrieval.results import load_queries
from retrieval.search import Retriever
from retrieval.search.runner import run_queries


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--queries", default=str(ROOT / "queries" / "query.parquet"))
    ap.add_argument("--id-col", default="id")
    ap.add_argument("--text-col", default="query")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--out-dir", default=str(ROOT / "candidates"))
    ap.add_argument("--live", action="store_true", help="tìm trên alias (index.alias) thay vì collection theo cấu hình")
    ap.add_argument("--no-progress", action="store_true", help="không hiện thanh tiến độ")
    ap.add_argument("--fresh", action="store_true", help="bỏ checkpoint của lượt chạy dở, làm lại từ đầu")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    show = not a.no_progress
    s = load_all(Env())
    r = Retriever(s, make_client(s.env), build_embedder(s.embed), build_reranker(s.rerank),
                  collection=s.index.alias if a.live else None)
    with log_redirect(show):
        res = run_queries(s, r, load_queries(Path(a.queries), a.id_col, a.text_col, a.limit), Path(a.out_dir),
                          tqdm_bars(show), resume=not a.fresh)
    print(f"{res['run_id']} → {res['out']} | lỗi: {res['failed']}")
    return 1 if res["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())