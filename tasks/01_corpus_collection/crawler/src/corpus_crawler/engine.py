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
    settings: Settings,
    state: CrawlState,
    writer: ShardWriter,
    *,
    included_domains: frozenset[str] | None = None,
    max_fetches: int | None = None,
) -> None:
    if max_fetches is not None and max_fetches < 1:
        raise ValueError("max_fetches must be a positive integer.")
    connector = aiohttp.TCPConnector(limit=settings.global_concurrency)
    timeout = aiohttp.ClientTimeout(total=settings.timeout_seconds)
    headers = {"User-Agent": settings.user_agent}
    started = time.monotonic()
    last_report = started
    session_counts: Counter[str] = Counter()
    stop = asyncio.Event()
    in_flight_domains: set[str] = set()
    reserved_fetches = 0
    fetcher: RespectfulFetcher
    async with aiohttp.ClientSession(
        connector=connector, timeout=timeout, headers=headers
    ) as session:
        fetcher = RespectfulFetcher(settings, session)

        async def worker() -> None:
            nonlocal last_report, reserved_fetches
            while not stop.is_set():
                if max_fetches is not None and reserved_fetches >= max_fetches:
                    return
                row = state.claim_next(
                    settings.excluded_domains,
                    frozenset(in_flight_domains),
                    included_domains,
                )
                if row is None:
                    if state.pending_count(
                        settings.excluded_domains, included_domains
                    ) == 0:
                        return
                    await asyncio.sleep(0.05)
                    continue
                reserved_fetches += 1
                domain = str(row["domain"])
                in_flight_domains.add(domain)
                try:
                    request_started = time.monotonic()
                    result = await fetcher.fetch(str(row["url"]), domain)
                    log_record, doc_record = await asyncio.to_thread(
                        make_records,
                        int(row["id"]),
                        str(row["url"]),
                        domain,
                        result,
                        settings,
                    )
                    state.save_result(
                        int(row["id"]),
                        result.attempts,
                        log_record,
                        doc_record,
                        elapsed_seconds=time.monotonic() - request_started,
                        fetch_succeeded=result.status == "ok",
                    )
                    session_counts[log_record["status"]] += 1
                    writer.export_ready()
                    now = time.monotonic()
                    if now - last_report >= settings.progress_seconds:
                        total, done, pending = state.totals(
                            settings.excluded_domains, included_domains
                        )
                        elapsed = max(now - started, 0.001)
                        rate = sum(session_counts.values()) / elapsed
                        eta_seconds = pending / rate if rate else 0.0
                        status_counts = state.completed_counts(
                            settings.excluded_domains, included_domains
                        )
                        status_labels = {
                            "blocked": "bị chặn",
                            "too_short": "quá ngắn",
                            "ok": "đạt",
                            "empty": "rỗng",
                            "http_error": "lỗi HTTP",
                            "timeout": "quá giờ",
                            "lang_mismatch": "sai ngôn ngữ",
                            "duplicate": "trùng lặp",
                        }
                        status_summary = " | ".join(
                            f"{status_labels[status]} ({status}) "
                            f"{status_counts.get(status, 0):,}"
                            for status in (
                                "blocked",
                                "too_short",
                                "ok",
                                "empty",
                                "http_error",
                                "timeout",
                                "lang_mismatch",
                                "duplicate",
                            )
                        )
                        print(
                            f"\rTiến độ A: {done:,}/{total:,} | còn lại {pending:,} | "
                            f"{status_summary} | {rate:.2f} URL/s | "
                            f"còn khoảng {eta_seconds / 3600:.1f} giờ",
                            end="",
                            flush=True,
                        )
                        last_report = now
                finally:
                    in_flight_domains.discard(domain)

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
    total, done, pending = state.totals(
        settings.excluded_domains, included_domains
    )
    excluded_pending = state.totals()[2] - pending
    scope = (
        f" in domain(s) {', '.join(sorted(included_domains))}"
        if included_domains is not None
        else ""
    )
    limit_message = (
        f" (limit {max_fetches:,} URL fetches)"
        if max_fetches is not None
        else ""
    )
    print(
        f"\nHoàn tất lượt crawl{scope}{limit_message}: "
        f"{sum(session_counts.values()):,} URL; "
        f"đủ điều kiện {done:,}/{total:,}, còn lại {pending:,}; "
        f"đang loại trừ {excluded_pending:,} URL chưa crawl; "
        f"trạng thái={dict(session_counts)}"
    )
