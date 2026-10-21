"""python -m submission.run_submit --candidates candidates/<run_id>.jsonl [--queries queries/query.jsonl] [--note "..."]
   → submissions/<tên>.zip (một file .json ở gốc) + dòng mới trong reports/submissions.csv. Có lỗi thì không tạo file."""
import argparse
from pathlib import Path
from common.config import Env, ROOT, load_cfg
from retrieval.results import load_queries, read_results
from .settings import SubmitCfg
from .run import SubmissionRejected, make_submission
from .sources import load_id_set


def _abs(p: Path) -> Path:
    return p if p.is_absolute() else ROOT / p


def main() -> int:
    cfg = load_cfg("submit", SubmitCfg, Env())
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidates", default=str(cfg.candidates_path))
    ap.add_argument("--queries", default=str(ROOT / "queries" / "query.parquet"), help="tập truy vấn của BTC: để kiểm tra đủ mọi id")
    ap.add_argument("--id-col", default="id")
    ap.add_argument("--text-col", default="query")
    ap.add_argument("--name", default=None, help="tên file zip (mặc định: tên file candidates)")
    ap.add_argument("--out-dir", default=str(cfg.output_dir))
    ap.add_argument("--note", default="")
    a = ap.parse_args()

    cand = _abs(Path(a.candidates))
    expected = {q.qid for q in load_queries(_abs(Path(a.queries)), a.id_col, a.text_col)}
    ids_path = _abs(cfg.check.btc_ids_path) if cfg.check.btc_ids_path else None
    known = load_id_set(ids_path) if ids_path and ids_path.exists() else None
    try:
        res = make_submission(cfg, list(read_results(cand)), _abs(Path(a.out_dir)), a.name or cand.stem, expected, known,
                              log_csv=_abs(cfg.log_csv), note=a.note)
    except SubmissionRejected as e:
        print(e)
        return 1
    for w in res["warnings"]:
        print(w)
    print(f"→ {res['zip']} | {res['n_queries']} truy vấn, {res['docs_total']} doc, {res['chunks_total']} chunk, "
          f"{res['queries_without_docs']} truy vấn trống | sha256 {res['sha256'][:12]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())