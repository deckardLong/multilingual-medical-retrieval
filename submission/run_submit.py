"""python -m submission.run_submit --candidates candidates/<run_id>.jsonl [--queries queries/query.jsonl] [--note "..."]
   → submissions/<tên>.zip (một file .json ở gốc) + dòng mới trong reports/submissions.csv. Có lỗi thì không tạo file."""
import argparse
from pathlib import Path
from common.config import Env, ROOT, load_cfg
from retrieval.results import load_queries, read_results
from .settings import SubmitCfg
from .run import SubmissionRejected, make_submission
from .expand import load_texts, needed_uids
from .sources import load_id_set


def _abs(p: Path) -> Path:
    return p if p.is_absolute() else ROOT / p


def main() -> int:
    env = Env()
    cfg = load_cfg("submit", SubmitCfg, env)
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidates", default=str(cfg.candidates_path))
    ap.add_argument("--queries", default=str(ROOT / "queries" / "query.parquet"), help="tập truy vấn của BTC: để kiểm tra đủ mọi id")
    ap.add_argument("--id-col", default="id")
    ap.add_argument("--text-col", default="query")
    ap.add_argument("--name", default=None, help="tên file zip (mặc định: tên file candidates)")
    ap.add_argument("--out-dir", default=str(cfg.output_dir))
    ap.add_argument("--note", default="")
    ap.add_argument("--int-doc-ids", action="store_true", help="ghi doc_id dạng số nguyên thay vì chuỗi")
    ap.add_argument("--expand-words", type=int, default=None, help="nới mỗi chunk ra các câu kề trong doc gốc tới ~N từ")
    ap.add_argument("--max-chunks", type=int, default=None, help="tối đa N chunk mỗi truy vấn (giữ chunk điểm cao trước)")
    a = ap.parse_args()
    if a.int_doc_ids:
        cfg = cfg.model_copy(update={"int_doc_ids": True})
    if a.expand_words is not None:
        cfg = cfg.model_copy(update={"build": cfg.build.model_copy(update={"expand_to_words": a.expand_words})})
    if a.max_chunks is not None:
        cfg = cfg.model_copy(update={"build": cfg.build.model_copy(update={"max_chunks": a.max_chunks})})

    cand = _abs(Path(a.candidates))
    expected = {q.qid for q in load_queries(_abs(Path(a.queries)), a.id_col, a.text_col)}
    ids_path = _abs(cfg.check.btc_ids_path) if cfg.check.btc_ids_path else None
    known = load_id_set(ids_path) if ids_path and ids_path.exists() else None
    results = list(read_results(cand))
    texts = None
    if cfg.build.expand_to_words:
        uids = needed_uids(results)
        print(f"đọc text gốc của {len(uids)} doc từ shard để nới chunk tới ~{cfg.build.expand_to_words} từ…")
        texts = load_texts(_abs(env.r2ai_corpus_dir) / "viz" / "docs", uids)
        if len(texts) < len(uids):
            print(f"WARNING {len(uids) - len(texts)} doc không tìm thấy text gốc: giữ nguyên chunk của chúng")
    try:
        res = make_submission(cfg, results, _abs(Path(a.out_dir)), a.name or cand.stem, expected, known,
                              log_csv=_abs(cfg.log_csv), note=a.note, texts=texts)
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