from __future__ import annotations

import asyncio
import time
from collections import Counter

import aiohttp

from .extract import make_records
from .fetch import RespectfulFetcher
from .output import ShardWriter
from .settings import Settings
from .state import CrawlState


async def run_crawl(
    settings: Settings, state: CrawlState, writer: ShardWriter
) -> None:
    connector = aiohttp.TCPConnector(limit=settings.global_concurrency)
    timeout = aiohttp.ClientTimeout(total=settings.timeout_seconds)
    headers = {"User-Agent": settings.user_agent}
    started = time.monotonic()
    last_report = started
    session_counts: Counter[str] = Counter()
    stop = asyncio.Event()
    fetcher: RespectfulFetcher
    async with aiohttp.ClientSession(
        connector=connector, timeout=timeout, headers=headers
    ) as session:
        fetcher = RespectfulFetcher(settings, session)

        async def worker() -> None:
            nonlocal last_report
            while not stop.is_set():
                row = state.claim_next()
                if row is None:
                    if state.pending_count() == 0:
                        return
                    await asyncio.sleep(0.05)
                    continue
                result = await fetcher.fetch(str(row["url"]), str(row["domain"]))
                log_record, doc_record = await asyncio.to_thread(
                    make_records,
                    int(row["id"]),
                    str(row["url"]),
                    str(row["domain"]),
                    result,
                    settings,
                )
                state.save_result(
                    int(row["id"]), result.attempts, log_record, doc_record
                )
                session_counts[log_record["status"]] += 1
                writer.export_ready()
                now = time.monotonic()
                if now - last_report >= settings.progress_seconds:
                    total, done, pending = state.totals()
                    elapsed = max(now - started, 0.001)
                    rate = sum(session_counts.values()) / elapsed
                    eta_seconds = pending / rate if rate else 0.0
                    print(
                        f"\rProgress {done:,}/{total:,} | remaining {pending:,} | "
                        f"{rate:.2f} URL/s | ETA {eta_seconds / 3600:.1f} h",
                        end="",
                        flush=True,
                    )
                    last_report = now

        workers = [
            asyncio.create_task(worker())
            for _ in range(settings.global_concurrency)
        ]
        try:
            await asyncio.gather(*workers)
        except BaseException:
            stop.set()
            for task in workers:
                task.cancel()
            await asyncio.gather(*workers, return_exceptions=True)
            raise
        finally:
            writer.export_ready(force=True)
    total, done, pending = state.totals()
    print(
        f"\nFinished this run: {sum(session_counts.values()):,} URLs; "
        f"overall {done:,}/{total:,}, remaining {pending:,}; "
        f"statuses={dict(session_counts)}"
    )
