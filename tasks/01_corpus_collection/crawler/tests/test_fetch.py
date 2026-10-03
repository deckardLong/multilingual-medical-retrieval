import asyncio
from dataclasses import replace

from aiohttp import ClientSession, web
from aiohttp.test_utils import TestServer

from corpus_crawler.fetch import RespectfulFetcher
from corpus_crawler.settings import load_settings


def test_robots_policy_and_external_redirects() -> None:
    async def run() -> None:
        async def robots(_request: web.Request) -> web.Response:
            _ = _request
            return web.Response(
                text="User-agent: *\nAllow: /\nDisallow: /private\n"
            )

        async def page(_request: web.Request) -> web.Response:
            _ = _request
            return web.Response(text="ok")

        async def external(_request: web.Request) -> web.HTTPFound:
            _ = _request
            raise web.HTTPFound("http://example.com/not-requested")

        app = web.Application()
        app.router.add_get("/robots.txt", robots)
        app.router.add_get("/page", page)
        app.router.add_get("/private", page)
        app.router.add_get("/external", external)
        server = TestServer(app)
        await server.start_server()
        settings = replace(
            load_settings(),
            domains=frozenset({"127.0.0.1"}),
            requests_per_domain=100,
            max_retries=0,
        )
        try:
            async with ClientSession(
                headers={"User-Agent": settings.user_agent}
            ) as session:
                fetcher = RespectfulFetcher(settings, session)
                base_url = str(server.make_url("/")).rstrip("/")

                allowed = await fetcher.fetch(f"{base_url}/page", "127.0.0.1")
                assert allowed.status == "ok"
                assert allowed.body == b"ok"

                disallowed = await fetcher.fetch(
                    f"{base_url}/private", "127.0.0.1"
                )
                assert disallowed.status == "blocked"
                assert "robots" in (disallowed.error or "").lower()

                redirect = await fetcher.fetch(
                    f"{base_url}/external", "127.0.0.1"
                )
                assert redirect.status == "blocked"
                assert "Cross-domain" in (redirect.error or "")
        finally:
            await server.close()

    asyncio.run(run())
