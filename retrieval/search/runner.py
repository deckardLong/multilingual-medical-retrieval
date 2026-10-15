import time
from pathlib import Path
from retrieval.results import Query, QueryResult, read_results, write_json, write_results
from retrieval.select import select


def _to_results(queries: list[Query], pools) -> list[QueryResult]:
    return [QueryResult(qid=q.qid, query=q.text, candidates=p) for q, p in zip(queries, pools)]


def _select_all(pool_results: list[QueryResult], select_cfg) -> list[QueryResult]:
    return [QueryResult(qid=r.qid, query=r.query, candidates=select(r.candidates, select_cfg).chunks)
            for r in pool_results]


def run_queries(settings, retriever, queries: list[Query], out_dir: Path) -> dict:
    """Truy hồi + rerank cho toàn bộ truy vấn → <run_id>.pool.jsonl, rồi chọn → <run_id>.jsonl + run_card.json."""
    t0 = time.time()
    pools, errors = retriever.pools([q.text for q in queries])
    pool_results = _to_results(queries, pools)
    run_id = settings.run_id()
    pool_path, out_path = out_dir / f"{run_id}.pool.jsonl", out_dir / f"{run_id}.jsonl"
    write_results(pool_path, pool_results)
    write_results(out_path, _select_all(pool_results, settings.retrieve.select))
    card = settings.run_card() | dict(
        run_id=run_id, n_queries=len(queries), seconds=round(time.time() - t0, 1), pool_file=pool_path.name,
        failed_qids=[queries[i].qid for i in sorted(errors)], errors={str(queries[i].qid): e for i, e in errors.items()})
    write_json(out_dir / f"{run_id}.run_card.json", card)
    return dict(run_id=run_id, out=out_path, pool=pool_path, failed=card["failed_qids"])


def run_select(settings, pool_path: Path, out_dir: Path) -> dict:
    """Chọn lại từ pool đã có theo select.* hiện hành (không cần GPU/Qdrant)."""
    pool_results = list(read_results(pool_path))
    run_id = settings.run_id()
    out_path = out_dir / f"{run_id}.jsonl"
    write_results(out_path, _select_all(pool_results, settings.retrieve.select))
    write_json(out_dir / f"{run_id}.run_card.json", settings.run_card() | dict(
        run_id=run_id, n_queries=len(pool_results), pool_file=Path(pool_path).name, reselected=True))
    return dict(run_id=run_id, out=out_path)