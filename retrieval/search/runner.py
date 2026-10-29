import logging
import time
from pathlib import Path
from retrieval.progress import no_bars
from retrieval.results import Query, QueryResult, read_results, write_json, write_results
from retrieval.select import select
from .checkpoint import Checkpoint

log = logging.getLogger(__name__)


def _to_results(queries: list[Query], pools) -> list[QueryResult]:
    return [QueryResult(qid=q.qid, query=q.text, candidates=p) for q, p in zip(queries, pools)]


def _select_all(pool_results: list[QueryResult], select_cfg, make_bar=no_bars) -> list[QueryResult]:
    out = []
    with make_bar("Chọn chunk", len(pool_results), "q") as bar:
        for r in pool_results:
            out.append(QueryResult(qid=r.qid, query=r.query, candidates=select(r.candidates, select_cfg).chunks))
            bar.advance()
    return out


def run_queries(settings, retriever, queries: list[Query], out_dir: Path, make_bar=no_bars, resume: bool = True) -> dict:
    """Truy hồi + rerank cho toàn bộ truy vấn → <run_id>.pool.jsonl, rồi chọn → <run_id>.jsonl + run_card.json.
    Mỗi truy vấn xong được ghi ngay vào checkpoint; bị ngắt thì chạy lại sẽ chỉ làm phần còn thiếu (resume=False: làm lại từ đầu).
    Checkpoint chỉ bị xoá khi mọi truy vấn đều thành công, nên truy vấn lỗi sẽ được thử lại ở lần sau."""
    t0 = time.time()
    ckpt = Checkpoint(Path(out_dir) / f".resume-{settings.pool_key()}.jsonl")
    if not resume:
        ckpt.clear()
    done = ckpt.load(queries)
    todo = [q for q in queries if q.qid not in done]
    if done:
        log.info("Nối tiếp lượt chạy dở: đã có %d/%d truy vấn, còn %d", len(done), len(queries), len(todo))
    try:
        new_pools, new_errors = retriever.pools(
            [q.text for q in todo], make_bar,
            on_done=lambda i, pool: ckpt.add(QueryResult(qid=todo[i].qid, query=todo[i].text, candidates=pool)))
    finally:
        ckpt.close()
    got = done | {q.qid: p for q, p in zip(todo, new_pools)}
    pools = [got[q.qid] for q in queries]
    pos = {q.qid: i for i, q in enumerate(queries)}
    errors = {pos[todo[j].qid]: e for j, e in new_errors.items()}
    pool_results = _to_results(queries, pools)
    run_id = settings.run_id()
    pool_path, out_path = out_dir / f"{run_id}.pool.jsonl", out_dir / f"{run_id}.jsonl"
    write_results(pool_path, pool_results)
    write_results(out_path, _select_all(pool_results, settings.retrieve.select))
    card = settings.run_card() | dict(
        run_id=run_id, n_queries=len(queries), resumed=len(done), seconds=round(time.time() - t0, 1),
        pool_file=pool_path.name, failed_qids=[queries[i].qid for i in sorted(errors)],
        errors={str(queries[i].qid): e for i, e in errors.items()})
    write_json(out_dir / f"{run_id}.run_card.json", card)
    if not errors:
        ckpt.clear()
    return dict(run_id=run_id, out=out_path, pool=pool_path, failed=card["failed_qids"])


def latest_pool(out_dir: Path) -> Path:
    """File *.pool.jsonl mới nhất trong out_dir."""
    pools = sorted(Path(out_dir).glob("*.pool.jsonl"), key=lambda p: p.stat().st_mtime)
    if not pools:
        raise FileNotFoundError(f"không có *.pool.jsonl nào trong {out_dir}; chạy retrieval.run_queries trước hoặc chỉ định --pool")
    return pools[-1]


def run_select(settings, pool_path: Path, out_dir: Path, make_bar=no_bars) -> dict:
    """Chọn lại từ pool đã có theo select.* hiện hành (không cần GPU/Qdrant). Chỉ mất vài giây nên không có checkpoint."""
    pool_results = list(read_results(pool_path))
    run_id = settings.run_id()
    out_path = out_dir / f"{run_id}.jsonl"
    write_results(out_path, _select_all(pool_results, settings.retrieve.select, make_bar))
    write_json(out_dir / f"{run_id}.run_card.json", settings.run_card() | dict(
        run_id=run_id, n_queries=len(pool_results), pool_file=Path(pool_path).name, reselected=True))
    return dict(run_id=run_id, out=out_path)