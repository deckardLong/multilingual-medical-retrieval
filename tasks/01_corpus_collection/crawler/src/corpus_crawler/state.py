from __future__ import annotations

import json
import math
import sqlite3
import time
from pathlib import Path
from typing import Any, TypedDict

from .settings import Settings
from .source import iter_source_rows, source_row_count
from .text import normalize_hostname


DOMAIN_WARMUP_SAMPLES = 3


class DomainPerformance(TypedDict):
    domain: str
    sample_count: int
    success_rate: float
    mean_seconds: float
    standard_deviation: float
    conservative_rate: float


class CrawlState:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA synchronous=FULL")
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS urls (
                id INTEGER PRIMARY KEY,
                url TEXT NOT NULL,
                domain TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                attempt INTEGER NOT NULL DEFAULT 0,
                log_json TEXT,
                doc_json TEXT,
                doc_shard TEXT,
                log_exported INTEGER NOT NULL DEFAULT 0,
                doc_exported INTEGER NOT NULL DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS urls_pending ON urls(status, id);
            CREATE INDEX IF NOT EXISTS urls_logs ON urls(log_exported, id);
            CREATE INDEX IF NOT EXISTS urls_docs ON urls(doc_exported, id);
            CREATE TABLE IF NOT EXISTS content_hashes (
                content_hash TEXT PRIMARY KEY,
                uid TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS domain_stats (
                domain TEXT PRIMARY KEY,
                sample_count INTEGER NOT NULL DEFAULT 0,
                successful_count INTEGER NOT NULL DEFAULT 0,
                mean_seconds REAL NOT NULL DEFAULT 0,
                m2_seconds REAL NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS export_batches (
                batch_id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL,
                filename TEXT NOT NULL,
                manifest_filename TEXT,
                ids_json TEXT NOT NULL,
                state TEXT NOT NULL DEFAULT 'prepared'
            );
            """
        )

    def prepare_source(self, settings: Settings, limit: int | None) -> tuple[int, int]:
        if limit is not None and limit < 1:
            raise ValueError("--limit must be a positive number of assigned URLs.")
        stat = settings.input_parquet.stat()
        fingerprint = json.dumps(
            {
                "path": str(settings.input_parquet.resolve()),
                "size": stat.st_size,
                "mtime_ns": stat.st_mtime_ns,
            },
            sort_keys=True,
        )
        existing = self.connection.execute(
            "SELECT value FROM metadata WHERE key='input_fingerprint'"
        ).fetchone()
        if existing is not None and existing["value"] != fingerprint:
            try:
                previous_fingerprint = json.loads(existing["value"])
            except json.JSONDecodeError:
                previous_fingerprint = {}
            if (
                not isinstance(previous_fingerprint, dict)
                or previous_fingerprint.get("size") != stat.st_size
                or previous_fingerprint.get("mtime_ns") != stat.st_mtime_ns
            ):
                raise ValueError(
                    "Input Parquet changed since this checkpoint was created. "
                    "Use a new state DB; do not delete the old checkpoint."
                )
            self.connection.execute(
                "UPDATE metadata SET value=? WHERE key='input_fingerprint'",
                (fingerprint,),
            )
            self.connection.commit()
        seeded = self.connection.execute(
            "SELECT value FROM metadata WHERE key='source_seeded'"
        ).fetchone()
        if seeded is not None and seeded["value"] == "1":
            self.connection.execute(
                "UPDATE urls SET status='pending' WHERE status='fetching'"
            )
            self.connection.commit()
            return 0, 0
        self.connection.execute(
            "INSERT OR IGNORE INTO metadata(key, value) VALUES('input_fingerprint', ?)",
            (fingerprint,),
        )
        self.connection.execute(
            "UPDATE urls SET status='pending' WHERE status='fetching'"
        )
        self.connection.commit()

        added = 0
        scanned = 0
        selected = 0
        next_report = time.monotonic() + 5
        input_total = source_row_count(settings.input_parquet)
        batch: list[tuple[int, str, str]] = []
        for source_id, url in iter_source_rows(settings.input_parquet):
            scanned += 1
            now = time.monotonic()
            if now >= next_report:
                print(
                    f"\rIndexing input: {scanned:,}/{input_total:,} rows; "
                    f"A-assigned {selected:,}",
                    end="",
                    flush=True,
                )
                next_report = now + 5
            domain = normalize_hostname(url)
            if domain not in settings.domains:
                continue
            selected += 1
            batch.append((source_id, url, domain))
            if len(batch) >= 5000:
                added += self._insert_source_batch(batch)
                batch.clear()
            if limit is not None and selected >= limit:
                break
        if batch:
            added += self._insert_source_batch(batch)
        if scanned:
            print(
                f"\rIndexed input: {scanned:,}/{input_total:,} rows; "
                f"A-assigned {selected:,}"
            )
        if limit is None:
            registered = self.totals()[0]
            if registered != selected:
                raise ValueError(
                    "The number of unique assigned source IDs does not match the "
                    f"source rows ({registered:,} registered, {selected:,} assigned). "
                    "Check that BTC IDs are unique before crawling."
                )
            with self.connection:
                self.connection.execute(
                    "INSERT OR REPLACE INTO metadata(key, value) VALUES('source_seeded', '1')"
                )
        return added, scanned

    def _insert_source_batch(self, rows: list[tuple[int, str, str]]) -> int:
        cursor = self.connection.executemany(
            "INSERT OR IGNORE INTO urls(id, url, domain) VALUES(?, ?, ?)", rows
        )
        self.connection.commit()
        return cursor.rowcount

    def claim_next(
        self,
        excluded_domains: frozenset[str] = frozenset(),
        in_flight_domains: frozenset[str] = frozenset(),
        included_domains: frozenset[str] | None = None,
    ) -> sqlite3.Row | None:
        filters = ["u.status='pending'"]
        parameters: list[str] = []
        if included_domains is not None:
            if not included_domains:
                filters.append("0")
            else:
                placeholders = ",".join("?" for _ in included_domains)
                filters.append(f"u.domain IN ({placeholders})")
                parameters.extend(sorted(included_domains))
        if excluded_domains:
            placeholders = ",".join("?" for _ in excluded_domains)
            filters.append(f"u.domain NOT IN ({placeholders})")
            parameters.extend(sorted(excluded_domains))
        if in_flight_domains:
            placeholders = ",".join("?" for _ in in_flight_domains)
            filters.append(f"u.domain NOT IN ({placeholders})")
            parameters.extend(sorted(in_flight_domains))
        candidates = self.connection.execute(
            f"""
            SELECT u.domain, MIN(u.id) AS next_id,
                   COALESCE(ds.sample_count, 0) AS sample_count,
                   COALESCE(ds.successful_count, 0) AS successful_count,
                   COALESCE(ds.mean_seconds, 0) AS mean_seconds,
                   COALESCE(ds.m2_seconds, 0) AS m2_seconds
            FROM urls AS u
            LEFT JOIN domain_stats AS ds ON ds.domain=u.domain
            WHERE {" AND ".join(filters)}
            GROUP BY u.domain
            """,
            parameters,
        ).fetchall()
        if not candidates:
            return None
        candidate = min(candidates, key=self._domain_priority)
        row = self.connection.execute(
            "SELECT id, url, domain FROM urls WHERE id=? AND status='pending'",
            (candidate["next_id"],),
        ).fetchone()
        if row is None:
            return None
        cursor = self.connection.execute(
            "UPDATE urls SET status='fetching' WHERE id=? AND status='pending'",
            (row["id"],),
        )
        self.connection.commit()
        return row if cursor.rowcount == 1 else None

    @staticmethod
    def _domain_priority(stats: sqlite3.Row) -> tuple[int, int, float, str]:
        sample_count = int(stats["sample_count"])
        domain = str(stats["domain"])
        if sample_count < DOMAIN_WARMUP_SAMPLES:
            return (0, sample_count, 0.0, domain)

        variance = float(stats["m2_seconds"]) / max(sample_count - 1, 1)
        standard_deviation = math.sqrt(max(variance, 0.0))
        mean_seconds = max(float(stats["mean_seconds"]), 0.001)
        success_rate = int(stats["successful_count"]) / sample_count
        conservative_rate = success_rate / (mean_seconds + standard_deviation)
        return (1, 0, -conservative_rate, domain)

    def save_result(
        self,
        source_id: int,
        attempts: int,
        log_record: dict[str, Any],
        doc_record: dict[str, Any] | None,
        *,
        elapsed_seconds: float | None = None,
        fetch_succeeded: bool = False,
    ) -> None:
        if elapsed_seconds is not None and (
            not math.isfinite(elapsed_seconds) or elapsed_seconds < 0
        ):
            raise ValueError("elapsed_seconds must be a finite, non-negative number.")
        with self.connection:
            if doc_record is not None:
                content_hash = doc_record["content_hash"]
                original = self.connection.execute(
                    "SELECT uid FROM content_hashes WHERE content_hash=?",
                    (content_hash,),
                ).fetchone()
                if original is not None:
                    doc_record["dup_of"] = original["uid"]
                    doc_record["fetch"]["status"] = "duplicate"
                    log_record["status"] = "duplicate"
                else:
                    self.connection.execute(
                        "INSERT INTO content_hashes(content_hash, uid) VALUES(?, ?)",
                        (content_hash, doc_record["uid"]),
                    )
            log_record["shard"] = None
            self.connection.execute(
                """
                UPDATE urls
                SET status='done', attempt=?, log_json=?, doc_json=?
                WHERE id=?
                """,
                (
                    attempts,
                    json.dumps(log_record, ensure_ascii=False),
                    (
                        json.dumps(doc_record, ensure_ascii=False)
                        if doc_record is not None
                        else None
                    ),
                    source_id,
                ),
            )
            if elapsed_seconds is not None:
                url_row = self.connection.execute(
                    "SELECT domain FROM urls WHERE id=?", (source_id,)
                ).fetchone()
                if url_row is None:
                    raise ValueError(f"Unknown source URL ID: {source_id}")
                domain = str(url_row["domain"])
                stats = self.connection.execute(
                    "SELECT sample_count, successful_count, mean_seconds, m2_seconds "
                    "FROM domain_stats WHERE domain=?",
                    (domain,),
                ).fetchone()
                sample_count = int(stats["sample_count"]) if stats else 0
                successful_count = int(stats["successful_count"]) if stats else 0
                mean_seconds = float(stats["mean_seconds"]) if stats else 0.0
                m2_seconds = float(stats["m2_seconds"]) if stats else 0.0
                sample_count += 1
                elapsed_seconds = max(elapsed_seconds, 0.001)
                delta = elapsed_seconds - mean_seconds
                mean_seconds += delta / sample_count
                m2_seconds += delta * (elapsed_seconds - mean_seconds)
                successful_count += int(fetch_succeeded)
                self.connection.execute(
                    """
                    INSERT OR REPLACE INTO domain_stats(
                        domain, sample_count, successful_count, mean_seconds, m2_seconds
                    ) VALUES(?, ?, ?, ?, ?)
                    """,
                    (
                        domain,
                        sample_count,
                        successful_count,
                        mean_seconds,
                        m2_seconds,
                    ),
                )

    def domain_performance(self) -> list[DomainPerformance]:
        rows = self.connection.execute(
            """
            SELECT domain, sample_count, successful_count, mean_seconds, m2_seconds
            FROM domain_stats
            WHERE EXISTS (
                SELECT 1 FROM urls
                WHERE urls.domain=domain_stats.domain AND urls.status='pending'
            )
            """
        ).fetchall()
        ranked = sorted(rows, key=self._domain_priority)
        performance: list[DomainPerformance] = []
        for row in ranked:
            sample_count = int(row["sample_count"])
            variance = float(row["m2_seconds"]) / max(sample_count - 1, 1)
            standard_deviation = math.sqrt(max(variance, 0.0))
            mean_seconds = float(row["mean_seconds"])
            success_rate = int(row["successful_count"]) / sample_count
            performance.append(
                {
                    "domain": str(row["domain"]),
                    "sample_count": sample_count,
                    "success_rate": success_rate,
                    "mean_seconds": mean_seconds,
                    "standard_deviation": standard_deviation,
                    "conservative_rate": success_rate
                    / max(mean_seconds + standard_deviation, 0.001),
                }
            )
        return performance

    def totals(
        self,
        excluded_domains: frozenset[str] = frozenset(),
        included_domains: frozenset[str] | None = None,
    ) -> tuple[int, int, int]:
        filters: list[str] = []
        parameters: list[str] = []
        if included_domains is not None:
            if not included_domains:
                filters.append("0")
            else:
                placeholders = ",".join("?" for _ in included_domains)
                filters.append(f"domain IN ({placeholders})")
                parameters.extend(sorted(included_domains))
        if excluded_domains:
            placeholders = ",".join("?" for _ in excluded_domains)
            filters.append(f"domain NOT IN ({placeholders})")
            parameters.extend(sorted(excluded_domains))
        where_clause = f" WHERE {' AND '.join(filters)}" if filters else ""
        row = self.connection.execute(
            f"""
            SELECT COUNT(*) AS total,
                   SUM(CASE WHEN status='done' THEN 1 ELSE 0 END) AS done,
                   SUM(CASE WHEN status!='done' THEN 1 ELSE 0 END) AS pending
            FROM urls{where_clause}
            """,
            parameters,
        ).fetchone()
        return int(row["total"] or 0), int(row["done"] or 0), int(row["pending"] or 0)

    def has_registered_urls(self) -> bool:
        row = self.connection.execute("SELECT 1 FROM urls LIMIT 1").fetchone()
        return row is not None

    def pending_count(
        self,
        excluded_domains: frozenset[str] = frozenset(),
        included_domains: frozenset[str] | None = None,
    ) -> int:
        filters = ["status='pending'"]
        parameters: list[str] = []
        if included_domains is not None:
            if not included_domains:
                filters.append("0")
            else:
                placeholders = ",".join("?" for _ in included_domains)
                filters.append(f"domain IN ({placeholders})")
                parameters.extend(sorted(included_domains))
        if excluded_domains:
            placeholders = ",".join("?" for _ in excluded_domains)
            filters.append(f"domain NOT IN ({placeholders})")
            parameters.extend(sorted(excluded_domains))
        row = self.connection.execute(
            f"SELECT COUNT(*) AS n FROM urls WHERE {' AND '.join(filters)}",
            parameters,
        ).fetchone()
        return int(row["n"] or 0)

    def completed_counts(self) -> dict[str, int]:
        rows = self.connection.execute(
            "SELECT json_extract(log_json, '$.status') AS result_status, COUNT(*) AS n "
            "FROM urls WHERE status='done' "
            "GROUP BY json_extract(log_json, '$.status')"
        ).fetchall()
        return {str(row["result_status"]): int(row["n"]) for row in rows}

    def rows_for_ids(self, ids: list[int]) -> list[sqlite3.Row]:
        placeholders = ",".join("?" for _ in ids)
        return list(
            self.connection.execute(
                f"SELECT * FROM urls WHERE id IN ({placeholders}) ORDER BY id", ids
            ).fetchall()
        )

    def reserve_batch(
        self, kind: str, filename: str, manifest_filename: str | None, ids: list[int]
    ) -> int:
        with self.connection:
            cursor = self.connection.execute(
                """
                INSERT INTO export_batches(kind, filename, manifest_filename, ids_json)
                VALUES(?, ?, ?, ?)
                """,
                (kind, filename, manifest_filename, json.dumps(ids)),
            )
            batch_id = cursor.lastrowid
            if batch_id is None:
                raise RuntimeError("SQLite did not return the reserved export batch ID.")
            return batch_id

    def pending_batches(self) -> list[sqlite3.Row]:
        return list(
            self.connection.execute(
                "SELECT * FROM export_batches WHERE state='prepared' ORDER BY batch_id"
            ).fetchall()
        )

    def finish_batch(self, batch_id: int, kind: str, ids: list[int], filename: str) -> None:
        field = "doc_exported" if kind == "docs" else "log_exported"
        with self.connection:
            if kind == "docs":
                self.connection.executemany(
                    f"UPDATE urls SET {field}=1, doc_shard=? WHERE id=?",
                    [(filename, source_id) for source_id in ids],
                )
            else:
                self.connection.executemany(
                    f"UPDATE urls SET {field}=1 WHERE id=?",
                    [(source_id,) for source_id in ids],
                )
            self.connection.execute(
                "UPDATE export_batches SET state='done' WHERE batch_id=?", (batch_id,)
            )

    def unexported_ids(self, kind: str, limit: int) -> list[int]:
        field = "doc_exported" if kind == "docs" else "log_exported"
        clause = "doc_json IS NOT NULL AND " if kind == "docs" else ""
        rows = self.connection.execute(
            f"SELECT id FROM urls WHERE status='done' AND {clause}{field}=0 "
            "ORDER BY id LIMIT ?",
            (limit,),
        ).fetchall()
        return [int(row["id"]) for row in rows]

    def close(self) -> None:
        self.connection.close()
