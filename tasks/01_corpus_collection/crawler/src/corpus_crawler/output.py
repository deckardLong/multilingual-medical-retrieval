from __future__ import annotations

import importlib.metadata
import json
import os
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
import zstandard

from .settings import Settings
from .state import CrawlState
from .validation import validate_doc, validate_shard_file


LOG_SCHEMA = pa.schema(
    [
        ("uid", pa.string()),
        ("id", pa.int64()),
        ("url", pa.string()),
        ("domain", pa.string()),
        ("owner", pa.string()),
        ("status", pa.string()),
        ("http_status", pa.int64()),
        ("attempt", pa.int64()),
        ("fetched_at", pa.string()),
        ("bytes", pa.int64()),
        ("final_url", pa.string()),
        ("error", pa.string()),
        ("shard", pa.string()),
    ]
)


def _next_sequence(directory: Path, pattern: str) -> int:
    directory.mkdir(parents=True, exist_ok=True)
    numbers = []
    for path in directory.glob(pattern):
        try:
            numbers.append(int(path.name.split("-")[-1].split(".")[0]))
        except ValueError:
            continue
    return max(numbers, default=0) + 1


class ShardWriter:
    def __init__(self, settings: Settings, state: CrawlState) -> None:
        self.settings = settings
        self.state = state
        root = settings.corpus_root / "viz"
        self.docs_dir = root / "docs" / settings.owner
        self.logs_dir = root / "crawl_log" / settings.owner
        self.manifests_dir = root / "manifest" / settings.owner
        for directory in (self.docs_dir, self.logs_dir, self.manifests_dir):
            directory.mkdir(parents=True, exist_ok=True)
        self.recover_batches()

    def recover_batches(self) -> None:
        for batch in self.state.pending_batches():
            ids = json.loads(batch["ids_json"])
            rows = self.state.rows_for_ids(ids)
            if batch["kind"] == "docs":
                path = self.docs_dir / batch["filename"]
                manifest_path = self.manifests_dir / str(batch["manifest_filename"])
                self._write_docs(path, manifest_path, rows, ids)
            else:
                path = self.logs_dir / batch["filename"]
                self._write_logs(path, rows)
            self.state.finish_batch(
                int(batch["batch_id"]), str(batch["kind"]), ids, str(batch["filename"])
            )

    def export_ready(self, force: bool = False) -> None:
        doc_count = len(self.state.unexported_ids("docs", self.settings.shard_docs))
        if doc_count >= self.settings.shard_docs or (force and doc_count):
            ids = self.state.unexported_ids("docs", self.settings.shard_docs)
            self._export_docs(ids)
        log_count = len(self.state.unexported_ids("logs", self.settings.shard_docs))
        if log_count >= self.settings.shard_docs or (force and log_count):
            doc_ids = self.state.unexported_ids("docs", self.settings.shard_docs)
            if doc_ids:
                self._export_docs(doc_ids)
            ids = self.state.unexported_ids("logs", self.settings.shard_docs)
            self._export_logs(ids)

    def _export_docs(self, ids: list[int]) -> None:
        seq = _next_sequence(self.docs_dir, f"viz-{self.settings.owner}-*.jsonl.zst")
        filename = f"viz-{self.settings.owner}-{seq:05d}.jsonl.zst"
        manifest_name = f"{filename}.manifest.json"
        batch_id = self.state.reserve_batch("docs", filename, manifest_name, ids)
        rows = self.state.rows_for_ids(ids)
        self._write_docs(
            self.docs_dir / filename, self.manifests_dir / manifest_name, rows, ids
        )
        self.state.finish_batch(batch_id, "docs", ids, filename)

    def _write_docs(
        self, path: Path, manifest_path: Path, rows: list[Any], ids: list[int]
    ) -> None:
        temp = path.with_suffix(path.suffix + ".tmp")
        temp_manifest = manifest_path.with_suffix(manifest_path.suffix + ".tmp")
        status_counts: Counter[str] = Counter()
        lang_counts: Counter[str] = Counter()
        with temp.open("wb") as raw:
            with zstandard.ZstdCompressor(level=3).stream_writer(
                raw, closefd=False
            ) as compressed:
                for row in rows:
                    if row["doc_json"] is None:
                        continue
                    doc = json.loads(row["doc_json"])
                    doc["fetch"]["status"] = (
                        "duplicate" if doc["dup_of"] else doc["fetch"]["status"]
                    )
                    validate_doc(doc, self.settings.owner)
                    status_counts[doc["fetch"]["status"]] += 1
                    lang_counts[doc["lang"]] += 1
                    compressed.write(
                        (json.dumps(doc, ensure_ascii=False) + "\n").encode("utf-8")
                    )
            raw.flush()
            os.fsync(raw.fileno())
        count, digest = validate_shard_file(temp, self.settings.owner)
        if count != sum(status_counts.values()):
            raise ValueError("Document count differs after writing the zstd shard")
        os.replace(temp, path)
        manifest = {
            "shard": path.name,
            "owner": self.settings.owner,
            "schema_version": self.settings.schema_version,
            "norm_version": self.settings.norm_version,
            "n_docs": count,
            "status_counts": dict(status_counts),
            "lang_counts": dict(lang_counts),
            "sha256": digest,
            "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "input": {"type": "domain_list", "value": "member_01.md"},
            "extractor": f"trafilatura@{importlib.metadata.version('trafilatura')}",
            "code_commit": self.settings.code_commit,
            "source_ids": ids,
        }
        try:
            temp_manifest.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            os.replace(temp_manifest, manifest_path)
        finally:
            if temp_manifest.exists():
                temp_manifest.unlink()

    def _export_logs(self, ids: list[int]) -> None:
        seq = _next_sequence(self.logs_dir, f"log-{self.settings.owner}-*.parquet")
        filename = f"log-{self.settings.owner}-{seq:05d}.parquet"
        batch_id = self.state.reserve_batch("logs", filename, None, ids)
        rows = self.state.rows_for_ids(ids)
        self._write_logs(self.logs_dir / filename, rows)
        self.state.finish_batch(batch_id, "logs", ids, filename)

    def _write_logs(self, path: Path, rows: list[Any]) -> None:
        records = []
        for row in rows:
            if row["log_json"] is None:
                continue
            record = json.loads(row["log_json"])
            if row["doc_shard"]:
                record["shard"] = row["doc_shard"]
            records.append(record)
        temp = path.with_suffix(path.suffix + ".tmp")
        pq.write_table(
            pa.Table.from_pylist(records, schema=LOG_SCHEMA), temp, compression="zstd"
        )
        os.replace(temp, path)
