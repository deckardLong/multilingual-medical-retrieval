from __future__ import annotations

import asyncio
from dataclasses import replace

from corpus_crawler import engine
from corpus_crawler.fetch import FetchResult
from corpus_crawler.output import ShardWriter
from corpus_crawler.settings import load_settings
from corpus_crawler.state import CrawlState


class _Fetcher:
    def __init__(self, settings, session) -> None:
        self.settings = settings
        self.session = session

    async def fetch(self, url: str, domain: str) -> FetchResult:
        return FetchResult(
            "blocked",
            None,
            "2026-10-11T00:00:00+07:00",
            None,
            None,
            f"robots.txt unavailable for {domain}: {url}",
            0,
            None,
        )


def test_run_crawl_limits_fetches_to_selected_domain(
    tmp_path, monkeypatch
) -> None:
    state = CrawlState(tmp_path / "state.sqlite3")
    selected_domain = "sggp.org.vn"
    other_domain = "cnkang.com"
    try:
        with state.connection:
            state.connection.executemany(
                "INSERT INTO urls(id, url, domain) VALUES(?, ?, ?)",
                [
                    (1, "https://www.sggp.org.vn/1", selected_domain),
                    (2, "https://www.sggp.org.vn/2", selected_domain),
                    (3, "https://www.sggp.org.vn/3", selected_domain),
                    (4, "https://www.sggp.org.vn/4", selected_domain),
                    (5, "https://www.cnkang.com/1", other_domain),
                    (6, "https://www.cnkang.com/2", other_domain),
                ],
            )
        monkeypatch.setattr(engine, "RespectfulFetcher", _Fetcher)
        def make_records(source_id, url, domain, result, settings):
            return {
                "id": source_id,
                "url": url,
                "domain": domain,
                "owner": settings.owner,
                "status": result.status,
            }, None

        monkeypatch.setattr(engine, "make_records", make_records)
        settings = replace(
            load_settings(),
            global_concurrency=5,
            excluded_domains=frozenset(),
            progress_seconds=60,
            corpus_root=tmp_path / "corpus",
        )

        asyncio.run(
            engine.run_crawl(
                settings,
                state,
                ShardWriter(settings, state),
                included_domains=frozenset({selected_domain}),
                max_fetches=3,
            )
        )

        assert state.totals(included_domains=frozenset({selected_domain})) == (
            4,
            3,
            1,
        )
        assert state.totals(included_domains=frozenset({other_domain})) == (
            2,
            0,
            2,
        )
    finally:
        state.close()
