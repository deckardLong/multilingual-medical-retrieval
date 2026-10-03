from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from datetime import datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin, urlsplit

import aiohttp
from protego import Protego

from .settings import Settings
from .text import normalize_hostname


@dataclass
class FetchResult:
    status: str
    http_status: int | None
    fetched_at: str
    final_url: str | None
    body: bytes | None
    error: str | None
    attempts: int
    nbytes: int | None
    encoding: str | None = None


def timestamp_now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


class RespectfulFetcher:
    def __init__(self, settings: Settings, session: aiohttp.ClientSession) -> None:
        self.settings = settings
        self.session = session
        self._domain_locks: dict[str, asyncio.Lock] = {}
        self._next_request: dict[str, float] = {}
        self._robots: dict[str, tuple[Protego, float]] = {}
        self._robots_failures: dict[str, tuple[str, float]] = {}
        self._robots_locks: dict[str, asyncio.Lock] = {}

    def _domain_lock(self, domain: str) -> asyncio.Lock:
        return self._domain_locks.setdefault(domain, asyncio.Lock())

    async def _robots_policy(
        self, url: str, domain: str
    ) -> tuple[Protego | None, float, str | None]:
        failure = self._robots_failures.get(domain)
        if failure is not None and time.monotonic() < failure[1]:
            return None, 0.0, failure[0]
        cached = self._robots.get(domain)
        if cached is not None and time.monotonic() < cached[1]:
            parser, _ = cached
            delay = parser.crawl_delay(self.settings.user_agent) or 0.0
            return parser, float(delay), None
        lock = self._robots_locks.setdefault(domain, asyncio.Lock())
        async with lock:
            failure = self._robots_failures.get(domain)
            if failure is not None and time.monotonic() < failure[1]:
                return None, 0.0, failure[0]
            cached = self._robots.get(domain)
            if cached is not None and time.monotonic() < cached[1]:
                parser, _ = cached
                delay = parser.crawl_delay(self.settings.user_agent) or 0.0
                return parser, float(delay), None
            parts = urlsplit(url)
            robots_url = f"{parts.scheme}://{parts.netloc}/robots.txt"
            try:
                async with self.session.get(
                    robots_url,
                    allow_redirects=False,
                    timeout=aiohttp.ClientTimeout(total=self.settings.timeout_seconds),
                ) as response:
                    if response.status == 404:
                        content = ""
                    elif response.status == 200:
                        content = (await response.content.read(512_000)).decode(
                            "utf-8", errors="replace"
                        )
                    else:
                        error = f"robots.txt returned HTTP {response.status}"
                        self._robots_failures[domain] = (
                            error,
                            time.monotonic() + 300,
                        )
                        return None, 0.0, error
            except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                error = f"robots.txt unavailable: {type(exc).__name__}"
                self._robots_failures[domain] = (error, time.monotonic() + 300)
                return None, 0.0, error
            parser = Protego.parse(content)
            self._robots[domain] = (parser, time.monotonic() + 3600)
            delay = parser.crawl_delay(user_agent=self.settings.user_agent) or 0.0
            return parser, float(delay), None

    async def fetch(self, url: str, domain: str) -> FetchResult:
        async with self._domain_lock(domain):
            parser, crawl_delay, robots_error = await self._robots_policy(url, domain)
            if robots_error:
                return FetchResult(
                    "blocked", None, timestamp_now(), None, None, robots_error, 0, None
                )
            if parser is None or not parser.can_fetch(
                url, user_agent=self.settings.user_agent
            ):
                return FetchResult(
                    "blocked",
                    None,
                    timestamp_now(),
                    None,
                    None,
                    "Disallowed by robots.txt",
                    0,
                    None,
                )

            configured_delay = 1.0 / self.settings.requests_per_domain
            delay = max(configured_delay, crawl_delay)
            attempts = 0
            last_error: str | None = None
            for attempt in range(self.settings.max_retries + 1):
                attempts += 1
                current_url = url
                redirects = 0
                retry_requested = False
                while True:
                    wait_for = self._next_request.get(domain, 0.0) - time.monotonic()
                    if wait_for > 0:
                        await asyncio.sleep(wait_for)
                    self._next_request[domain] = time.monotonic() + delay
                    try:
                        async with self.session.get(
                            current_url,
                            allow_redirects=False,
                            timeout=aiohttp.ClientTimeout(
                                total=self.settings.timeout_seconds
                            ),
                        ) as response:
                            if response.status in {301, 302, 303, 307, 308}:
                                location = response.headers.get("Location")
                                if not location or redirects >= 5:
                                    return FetchResult(
                                        "http_error",
                                        response.status,
                                        timestamp_now(),
                                        str(response.url),
                                        None,
                                        "Redirect missing Location or exceeded 5 hops",
                                        attempts,
                                        None,
                                    )
                                target = urljoin(str(response.url), location)
                                if normalize_hostname(target) != domain:
                                    return FetchResult(
                                        "blocked",
                                        response.status,
                                        timestamp_now(),
                                        target,
                                        None,
                                        "Cross-domain redirect not fetched",
                                        attempts,
                                        None,
                                    )
                                redirect_parser, _, redirect_error = (
                                    await self._robots_policy(target, domain)
                                )
                                if redirect_error or redirect_parser is None:
                                    return FetchResult(
                                        "blocked",
                                        response.status,
                                        timestamp_now(),
                                        target,
                                        None,
                                        redirect_error
                                        or "Could not verify redirect robots policy",
                                        attempts,
                                        None,
                                    )
                                if not redirect_parser.can_fetch(
                                    target, user_agent=self.settings.user_agent
                                ):
                                    return FetchResult(
                                        "blocked",
                                        response.status,
                                        timestamp_now(),
                                        target,
                                        None,
                                        "Redirect target disallowed by robots.txt",
                                        attempts,
                                        None,
                                    )
                                current_url = target
                                redirects += 1
                                continue

                            body = await response.content.read(
                                self.settings.max_response_bytes + 1
                            )
                            fetched_at = timestamp_now()
                            if len(body) > self.settings.max_response_bytes:
                                return FetchResult(
                                    "http_error",
                                    response.status,
                                    fetched_at,
                                    str(response.url),
                                    None,
                                    "Response exceeds configured size limit",
                                    attempts,
                                    len(body),
                                    response.charset,
                                )
                            if response.status == 403:
                                return FetchResult(
                                    "blocked",
                                    response.status,
                                    fetched_at,
                                    str(response.url),
                                    None,
                                    "HTTP 403; access not bypassed",
                                    attempts,
                                    len(body),
                                    response.charset,
                                )
                            if response.status in {408, 429} or response.status >= 500:
                                last_error = f"HTTP {response.status}"
                                retry_after = self._retry_after(
                                    response.headers.get("Retry-After")
                                )
                                if attempt < self.settings.max_retries:
                                    await asyncio.sleep(
                                        retry_after
                                        if retry_after is not None
                                        else self.settings.retry_backoff_seconds
                                        * (2**attempt)
                                    )
                                    retry_requested = True
                                    break
                            elif response.status >= 400:
                                return FetchResult(
                                    "http_error",
                                    response.status,
                                    fetched_at,
                                    str(response.url),
                                    None,
                                    f"HTTP {response.status}",
                                    attempts,
                                    len(body),
                                    response.charset,
                                )
                            else:
                                lowered = body[:8192].lower()
                                if (
                                    b"captcha" in lowered
                                    or b"verify you are human" in lowered
                                ):
                                    return FetchResult(
                                        "blocked",
                                        response.status,
                                        fetched_at,
                                        str(response.url),
                                        None,
                                        "Possible captcha/access challenge",
                                        attempts,
                                        len(body),
                                        response.charset,
                                    )
                                return FetchResult(
                                    "ok",
                                    response.status,
                                    fetched_at,
                                    str(response.url),
                                    body,
                                    None,
                                    attempts,
                                    len(body),
                                    response.charset,
                                )
                            return FetchResult(
                                "http_error",
                                response.status,
                                fetched_at,
                                str(response.url),
                                None,
                                f"HTTP {response.status}",
                                attempts,
                                len(body),
                                response.charset,
                            )
                    except asyncio.TimeoutError:
                        last_error = "Request timeout"
                        if attempt < self.settings.max_retries:
                            await asyncio.sleep(
                                self.settings.retry_backoff_seconds * (2**attempt)
                            )
                            retry_requested = True
                            break
                    except aiohttp.ClientError as exc:
                        last_error = f"{type(exc).__name__}: {exc}"
                        if attempt < self.settings.max_retries:
                            await asyncio.sleep(
                                self.settings.retry_backoff_seconds * (2**attempt)
                            )
                            retry_requested = True
                            break
                    if not retry_requested:
                        break

            status = "timeout" if last_error == "Request timeout" else "http_error"
            return FetchResult(
                status,
                None,
                timestamp_now(),
                None,
                None,
                last_error,
                attempts,
                None,
            )

    @staticmethod
    def _retry_after(value: str | None) -> float | None:
        if not value:
            return None
        try:
            return max(0.0, float(value))
        except ValueError:
            try:
                parsed = parsedate_to_datetime(value)
                return max(0.0, (parsed - datetime.now(parsed.tzinfo)).total_seconds())
            except (TypeError, ValueError, OverflowError):
                return None
