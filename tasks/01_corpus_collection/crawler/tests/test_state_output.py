import hashlib
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
