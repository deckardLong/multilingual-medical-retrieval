"""python -m corpus_sync.run_fetch [--dry-run] [--partition a|b] [--no-docs] [--queries-only]
   Tải kho ngữ liệu (B) + tập truy vấn (BTC) từ HuggingFace về chỗ retrieval/* đọc được, rồi sẵn sàng cho
   `python -m retrieval.run_index`. CHỈ CHẠY TRÊN MÁY CÓ MẠNG RA NGOÀI THẬT VÀ (để index) GPU."""
import argparse
from common.config import Env, ROOT, load_cfg
from .hf import fetch, plan
from .report import scan_local, summarize_plan
from .settings import SyncCfg


def _patterns(cfg: SyncCfg, a: argparse.Namespace) -> list[str]:
    if a.queries_only:
        return ["queries/query.parquet"]
    pats = list(cfg.allow_patterns)
    if a.no_docs:
        pats = [p for p in pats if "viz/docs" not in p]
    elif a.partition:
        pats = [p.replace("viz/docs/**", f"viz/docs/{a.partition}/**") for p in pats]
    return pats


def main() -> int:
    cfg = load_cfg("corpus_sync", SyncCfg, Env())
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="chỉ xem sẽ tải gì, không tải")
    ap.add_argument("--partition", choices=["a", "b"], default=None, help="chỉ tải shard doc của một phân vùng")
    ap.add_argument("--no-docs", action="store_true", help="bỏ shard doc, chỉ tải queries/links/schema (nhẹ, nhanh)")
    ap.add_argument("--queries-only", action="store_true")
    a = ap.parse_args()
    env = Env()
    patterns = _patterns(cfg, a)

    if a.dry_run:
        s = summarize_plan(plan(cfg, env, patterns))
        print(f"{s.n_to_download}/{s.n_files} file cần tải, {s.bytes_to_download / 1e6:.1f} MB")
        for prefix, (n, b) in s.by_prefix.items():
            print(f"  {prefix}: {n} file, {b / 1e6:.1f} MB")
        return 0

    fetch(cfg, env, patterns)
    ls = scan_local(env.r2ai_corpus_dir, ROOT / "queries" / "query.parquet", env.r2ai_corpus_dir / "raw" / "links_corpus.parquet")
    print(f"shard theo phân vùng: {ls.n_shards} | tổng {ls.bytes_total / 1e6:.1f} MB")
    print(f"links_corpus.parquet: {'có' if ls.has_links else 'CHƯA CÓ'} | query.parquet: {'có' if ls.has_queries else 'CHƯA CÓ'}")
    if not ls.has_links:
        print("CẢNH BÁO: thiếu links_corpus.parquet — submission.checks.ids sẽ không kiểm tra được doc_id")
    if not ls.has_queries:
        print("CẢNH BÁO: thiếu query.parquet")
    # chỉ coi là lỗi nếu thứ mình VỪA YÊU CẦU tải vẫn không có trên đĩa (vd --queries-only thì links vốn không tải)
    wanted_links = any("links_corpus.parquet" in p for p in patterns)
    wanted_queries = any(p.endswith("query.parquet") for p in patterns)
    return 1 if (wanted_links and not ls.has_links) or (wanted_queries and not ls.has_queries) else 0


if __name__ == "__main__":
    raise SystemExit(main())