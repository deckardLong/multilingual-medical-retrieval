import os
from pathlib import Path
from pydantic import ValidationError
from common.schema import Candidate
from retrieval.results import Query, QueryResult


class Checkpoint:
    """Pool của từng truy vấn được ghi nối vào file ngay khi xong; chạy lại thì đọc file này và bỏ qua những truy vấn đã có.
    Chỉ nhận lại kết quả khi cả qid lẫn nội dung truy vấn còn khớp."""

    def __init__(self, path: Path):
        self.path, self._f = Path(path), None

    def load(self, queries: list[Query]) -> dict[int, list[Candidate]]:
        if not self.path.exists():
            return {}
        want, done = {q.qid: q.text for q in queries}, {}
        with open(self.path, encoding="utf-8") as f:
            for line in f:
                try:
                    r = QueryResult.model_validate_json(line)
                except ValidationError:                     # dòng cuối dở dang do bị ngắt giữa lúc ghi
                    continue
                if want.get(r.qid) == r.query:
                    done[r.qid] = r.candidates
        return done

    def add(self, result: QueryResult) -> None:
        if self._f is None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            torn = self.path.exists() and self.path.stat().st_size > 0 and not self.path.read_bytes().endswith(b"\n")
            self._f = open(self.path, "a", encoding="utf-8")
            if torn:
                self._f.write("\n")
        self._f.write(result.model_dump_json() + "\n")
        self._f.flush(); os.fsync(self._f.fileno())

    def close(self) -> None:
        if self._f is not None:
            self._f.close(); self._f = None

    def clear(self) -> None:
        self.close(); self.path.unlink(missing_ok=True)
