import hashlib
import json
from dataclasses import replace

import pyarrow as pa
import pyarrow.parquet as pq

from corpus_crawler.output import ShardWriter
from corpus_crawler.settings import load_settings
from corpus_crawler.state import CrawlState
from corpus_crawler.validation import validate_shard_file


def _doc(source_id: int, text: str) -> dict:
    digest = "sha1:" + hashlib.sha1(text.encode("utf-8")).hexdigest()
    return {
        "schema_version": "1.0",
        "uid": f"vi:{source_id}",
        "doc_id": str(source_id),
        "lang": "vi",
        "source": "btc_url",
        "url": f"https://cnkang.com/{source_id}",
        "domain": "cnkang.com",
        "title": "Bài viết",
        "text": text,
        "norm_version": "n1",
        "passages": [{"type": "body", "start": 0, "end": len(text)}],
        "text_len": len(text),
        "content_hash": digest,
        "dup_of": None,
        "fetch": {
            "status": "ok",
            "http_status": 200,
            "fetched_at": "2026-10-02T00:00:00+07:00",
            "extractor": "trafilatura@test",
            "lang_detected": "vi",
            "lang_conf": 0.9,
        },
        "pubmed": None,
        "owner": "a",
        "code_commit": "test",
    }


def _log(source_id: int) -> dict:
    return {
        "uid": f"vi:{source_id}",
        "id": source_id,
        "url": f"https://cnkang.com/{source_id}",
        "domain": "cnkang.com",
        "owner": "a",
        "status": "ok",
        "http_status": 200,
        "attempt": 1,
        "fetched_at": "2026-10-02T00:00:00+07:00",
        "bytes": 100,
        "final_url": None,
        "error": None,
        "shard": None,
    }


def test_resume_filter_dedupe_and_export_recovery(tmp_path) -> None:
    source = tmp_path / "links.parquet"
    pq.write_table(
        pa.table(
            {
                "id": [1, 2, 3, 4],
                "url": [
                    "https://cnkang.com/1",
                    "http://www.cnkang.com/2",
                    "https://cnkang.com/3",
                    "https://foo.cnkang.com/4",
                ],
            }
        ),
        source,
    )
    settings = replace(
        load_settings(),
        input_parquet=source,
        corpus_root=tmp_path / "corpus",
        shard_docs=2,
    )
    state_path = tmp_path / "corpus" / "viz" / "state-a.sqlite3"
    state = CrawlState(state_path)
    try:
        added, _ = state.prepare_source(settings, None)
        assert added == 3
        assert state.totals() == (3, 0, 3)
        excluded = frozenset({"cnkang.com"})
        assert state.totals(excluded) == (0, 0, 0)
        assert state.pending_count(excluded) == 0
        assert state.claim_next(excluded) is None
        assert state.totals() == (3, 0, 3)
        assert state.prepare_source(settings, None) == (0, 0)

        shared_text = "Một bài viết y khoa để kiểm tra trùng nội dung."
        for source_id in (1, 2):
            state.save_result(source_id, 1, _log(source_id), _doc(source_id, shared_text))
        assert state.completed_counts() == {"duplicate": 1, "ok": 1}

        writer = ShardWriter(settings, state)
        writer.export_ready(force=True)
        first_shard = (
            settings.corpus_root
            / "viz"
            / "docs"
            / "a"
            / "viz-a-00001.jsonl.zst"
        )
        first_manifest = (
            settings.corpus_root
            / "viz"
            / "manifest"
            / "a"
            / f"{first_shard.name}.manifest.json"
        )
        assert validate_shard_file(first_shard, "a", first_manifest)[0] == 2
        log_shards = list(
            (settings.corpus_root / "viz" / "crawl_log" / "a").glob("*.parquet")
        )
        assert len(log_shards) == 1
        assert pq.read_table(log_shards[0]).num_rows == 2

        state.save_result(3, 1, _log(3), _doc(3, "Nội dung khác để thử resume."))
        batch_id = state.reserve_batch(
            "docs",
            "viz-a-00002.jsonl.zst",
            "viz-a-00002.jsonl.zst.manifest.json",
            [3],
        )
        assert batch_id > 0
        state.close()
        state = CrawlState(state_path)

        ShardWriter(settings, state)
        recovered_shard = (
            settings.corpus_root
            / "viz"
            / "docs"
            / "a"
            / "viz-a-00002.jsonl.zst"
        )
        recovered_manifest = (
            settings.corpus_root
            / "viz"
            / "manifest"
            / "a"
            / f"{recovered_shard.name}.manifest.json"
        )
        assert validate_shard_file(recovered_shard, "a", recovered_manifest)[0] == 1
        assert state.pending_batches() == []
        assert state.totals() == (3, 3, 0)
    finally:
        state.close()


def test_prepare_source_accepts_input_moved_without_changes(tmp_path) -> None:
    source = tmp_path / "links.parquet"
    pq.write_table(
        pa.table(
            {
                "id": [1],
                "url": ["https://cnkang.com/1"],
            }
        ),
        source,
    )
    settings = replace(
        load_settings(),
        input_parquet=source,
        corpus_root=tmp_path / "corpus",
    )
    state_path = settings.corpus_root / "viz" / "state-a.sqlite3"
    state = CrawlState(state_path)
    try:
        assert state.prepare_source(settings, None) == (1, 1)

        moved_source = tmp_path / "moved" / source.name
        moved_source.parent.mkdir()
        source.rename(moved_source)
        moved_settings = replace(settings, input_parquet=moved_source)

        assert state.prepare_source(moved_settings, None) == (0, 0)
        fingerprint = state.connection.execute(
            "SELECT value FROM metadata WHERE key='input_fingerprint'"
        ).fetchone()["value"]
        assert json.loads(fingerprint)["path"] == str(
            moved_settings.input_parquet.resolve()
        )
    finally:
        state.close()


def test_claim_next_samples_domains_then_prioritizes_stable_speed(tmp_path) -> None:
    state = CrawlState(tmp_path / "state.sqlite3")
    slow_domain = "cnkang.com"
    fast_domain = "ask.39.net"
    unstable_domain = "unstable.example"
    try:
        with state.connection:
            state.connection.executemany(
                "INSERT INTO urls(id, url, domain) VALUES(?, ?, ?)",
                [
                    (1, "https://cnkang.com/1", slow_domain),
                    (2, "https://cnkang.com/2", slow_domain),
                    (3, "https://cnkang.com/3", slow_domain),
                    (4, "https://cnkang.com/4", slow_domain),
                    (5, "https://ask.39.net/1", fast_domain),
                    (6, "https://ask.39.net/2", fast_domain),
                    (7, "https://ask.39.net/3", fast_domain),
                    (8, "https://ask.39.net/4", fast_domain),
                    (9, "https://unstable.example/1", unstable_domain),
                    (10, "https://unstable.example/2", unstable_domain),
                    (11, "https://unstable.example/3", unstable_domain),
                    (12, "https://unstable.example/4", unstable_domain),
                ],
            )

        first = state.claim_next()
        assert first is not None
        assert first["domain"] == fast_domain
        second = state.claim_next(in_flight_domains=frozenset({fast_domain}))
        assert second is not None
        assert second["domain"] == slow_domain

        for source_id, elapsed in (
            (1, 6.0),
            (2, 6.0),
            (3, 6.0),
            (5, 1.0),
            (6, 1.0),
            (7, 1.0),
            (9, 1.0),
            (10, 6.0),
            (11, 11.0),
        ):
            state.save_result(
                source_id,
                1,
                {"status": "ok"},
                None,
                elapsed_seconds=elapsed,
                fetch_succeeded=True,
            )

        state.close()
        state = CrawlState(tmp_path / "state.sqlite3")
        performance = state.domain_performance()
        assert performance[0]["domain"] == fast_domain
        assert performance[1]["domain"] == slow_domain
        assert performance[1]["conservative_rate"] > performance[2]["conservative_rate"]
        next_row = state.claim_next()
        assert next_row is not None
        assert next_row["domain"] == fast_domain
    finally:
        state.close()


def test_claim_next_can_be_scoped_to_included_domains(tmp_path) -> None:
    state = CrawlState(tmp_path / "state.sqlite3")
    try:
        with state.connection:
            state.connection.executemany(
                "INSERT INTO urls(id, url, domain) VALUES(?, ?, ?)",
                [
                    (1, "https://sggp.org.vn/1", "sggp.org.vn"),
                    (2, "https://cnkang.com/1", "cnkang.com"),
                ],
            )

        assert state.pending_count(
            included_domains=frozenset({"sggp.org.vn"})
        ) == 1
        assert state.totals(included_domains=frozenset({"sggp.org.vn"})) == (
            1,
            0,
            1,
        )
        row = state.claim_next(included_domains=frozenset({"sggp.org.vn"}))
        assert row is not None
        assert row["domain"] == "sggp.org.vn"
        assert state.claim_next(included_domains=frozenset()) is None
    finally:
        state.close()
