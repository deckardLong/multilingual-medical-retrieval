"""Dựng bài nộp từ C2: build → kiểm tra → ghi json → nén zip → mở lại zip để kiểm chứng → ghi nhật ký."""
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Sequence
from retrieval.chunking.tokens import build_counter
from retrieval.results import QueryResult
from .build import build_items
from .checks import Report, check_ids, check_items
from .log import append_log
from .pack import make_zip, read_zip, sha256, write_json
from .settings import SubmitCfg


class SubmissionRejected(Exception):
    """Bài nộp có lỗi: không ghi file nào."""

    def __init__(self, report: Report):
        super().__init__(f"{len(report.errors)} lỗi, không tạo bài nộp:\n{report}")
        self.report = report


def make_submission(cfg: SubmitCfg, results: Sequence[QueryResult], out_dir: Path, name: str,
                    expected_qids: set[int] | None, known_ids: set[str] | None, log_csv: Path | None = None,
                    note: str = "") -> dict:
    items = build_items(results, cfg.build)
    report = Report(tuple(check_ids(results, known_ids)
                          + check_items(items, expected_qids, cfg.check.max_chunk_tokens, build_counter(cfg.check.token_counter))))
    if not report.ok:
        raise SubmissionRejected(report)

    zip_path = Path(out_dir) / f"{name}.zip"
    with tempfile.TemporaryDirectory() as tmp:
        make_zip(write_json(items, Path(tmp) / cfg.json_name), zip_path, cfg.json_name)
    if read_zip(zip_path) != items:                            # file đem nộp phải đọc ngược ra đúng như đã dựng
        raise RuntimeError(f"{zip_path}: nội dung sau khi nén không khớp bản đã dựng")

    stats = dict(n_queries=len(items), docs_total=sum(len(i.relevant_docs) for i in items),
                 chunks_total=sum(len(i.relevant_chunks) for i in items),
                 queries_without_docs=sum(1 for i in items if not i.relevant_docs))
    digest = sha256(zip_path)
    if log_csv is not None:
        append_log(log_csv, dict(stats, time=datetime.now().astimezone().isoformat(timespec="seconds"),
                                 zip=zip_path.name, sha256=digest[:16], note=note))
    return dict(zip=zip_path, sha256=digest, warnings=report.warnings, **stats)