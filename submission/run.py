"""Dựng bài nộp từ C2: build → kiểm tra → ghi json → nén zip → mở lại zip để kiểm chứng → ghi nhật ký."""
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Sequence
from retrieval.chunking.tokens import build_counter
from retrieval.results import QueryResult
from .build import build_items
from .expand import Expander
from .checks import Report, check_ids, check_items
from .checks.problems import Problem, sample
from .log import append_log
from .pack import make_zip, read_zip, sha256, write_json
from .settings import SubmitCfg


def drop_unknown_ids(results: Sequence[QueryResult], known_ids: set[str] | None) -> tuple[list[QueryResult], list[Problem]]:
    """Doc có id ngoài danh sách BTC không bao giờ được tính điểm: bỏ khỏi bài nộp và báo một cảnh báo tổng hợp."""
    if known_ids is None:
        return list(results), []
    out, bad_docs, bad_queries = [], set(), 0
    for r in results:
        keep = [c for c in r.candidates if c.doc_id in known_ids]
        if len(keep) != len(r.candidates):
            bad_queries += 1
            bad_docs |= {c.doc_id for c in r.candidates if c.doc_id not in known_ids}
            r = r.model_copy(update={"candidates": keep})
        out.append(r)
    if not bad_docs:
        return out, []
    return out, [Problem("warning", f"bỏ {len(bad_docs)} doc_id không thuộc danh sách của BTC ở {bad_queries} truy vấn: "
                                    f"{sample(sorted(bad_docs))}")]


class SubmissionRejected(Exception):
    """Bài nộp có lỗi: không ghi file nào."""

    def __init__(self, report: Report):
        super().__init__(f"{len(report.errors)} lỗi, không tạo bài nộp:\n{report}")
        self.report = report


def make_submission(cfg: SubmitCfg, results: Sequence[QueryResult], out_dir: Path, name: str,
                    expected_qids: set[int] | None, known_ids: set[str] | None, log_csv: Path | None = None,
                    note: str = "", texts: dict[str, str] | None = None) -> dict:
    results, dropped = drop_unknown_ids(results, known_ids)
    expander = Expander(texts, cfg.build.expand_to_words) if cfg.build.expand_to_words and texts is not None else None
    items = build_items(results, cfg.build, expander)
    report = Report(tuple(dropped + check_ids(results, known_ids)
                          + check_items(items, expected_qids, cfg.check.max_chunk_tokens, build_counter(cfg.check.token_counter))))
    if not report.ok:
        raise SubmissionRejected(report)

    zip_path = Path(out_dir) / f"{name}.zip"
    with tempfile.TemporaryDirectory() as tmp:
        make_zip(write_json(items, Path(tmp) / cfg.json_name, cfg.int_doc_ids), zip_path, cfg.json_name)
    if read_zip(zip_path) != items:                            # file đem nộp phải đọc ngược ra đúng như đã dựng
        raise RuntimeError(f"{zip_path}: nội dung sau khi nén không khớp bản đã dựng")
    size_mb = zip_path.stat().st_size / 1e6
    if cfg.max_zip_mb is not None and size_mb > cfg.max_zip_mb:
        zip_path.unlink()
        raise SubmissionRejected(Report((Problem("error", f"file zip {size_mb:.1f} MB vượt giới hạn {cfg.max_zip_mb:g} MB; "
                                                          f"giảm build.max_chunks hoặc --expand-words"),)))

    stats = dict(n_queries=len(items), docs_total=sum(len(i.relevant_docs) for i in items),
                 chunks_total=sum(len(i.relevant_chunks) for i in items),
                 queries_without_docs=sum(1 for i in items if not i.relevant_docs))
    digest = sha256(zip_path)
    if log_csv is not None:
        append_log(log_csv, dict(stats, time=datetime.now().astimezone().isoformat(timespec="seconds"),
                                 zip=zip_path.name, sha256=digest[:16], note=note))
    return dict(zip=zip_path, sha256=digest, warnings=report.warnings, **stats)