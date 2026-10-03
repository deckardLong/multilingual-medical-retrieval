from __future__ import annotations

import hashlib
from typing import Any

import trafilatura

from .fetch import FetchResult
from .settings import Settings
from .text import detect_supported_language, normalize_text


def make_records(
    source_id: int,
    url: str,
    domain: str,
    result: FetchResult,
    settings: Settings,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    doc: dict[str, Any] | None = None
    status = result.status
    if result.status == "ok" and result.body is not None:
        try:
            downloaded = result.body.decode(result.encoding or "utf-8", errors="replace")
        except LookupError:
            downloaded = result.body.decode("utf-8", errors="replace")
        body = trafilatura.extract(
            downloaded,
            include_comments=False,
            include_tables=True,
            include_links=False,
            favor_precision=False,
            output_format="txt",
        )
        metadata = trafilatura.extract_metadata(downloaded)
        raw_title = metadata.title or "" if metadata else ""
        raw_article = body or ""
        title = normalize_text(raw_title)
        article = normalize_text(raw_article)
        if not article:
            status = "empty"
        else:
            content = normalize_text(
                f"{raw_title}\n\n{raw_article}" if raw_title else raw_article
            )
            if len(content) < settings.min_text_chars:
                status = "too_short"
            else:
                detected = detect_supported_language(content)
                if detected is None:
                    status = "lang_mismatch"
                else:
                    language, confidence = detected
                    if language not in {"vi", "zh"}:
                        status = "lang_mismatch"
                    sha1 = hashlib.sha1(content.encode("utf-8")).hexdigest()
                    passages: list[dict[str, Any]] = []
                    if title and content.startswith(title):
                        passages.append({"type": "title", "start": 0, "end": len(title)})
                        body_start = content.find(article, len(title))
                    else:
                        body_start = content.find(article)
                    if body_start >= 0 and article:
                        passages.append(
                            {
                                "type": "body",
                                "start": body_start,
                                "end": body_start + len(article),
                            }
                        )
                    doc = {
                        "schema_version": settings.schema_version,
                        "uid": f"{language}:{source_id}",
                        "doc_id": str(source_id),
                        "lang": language,
                        "source": "btc_url",
                        "url": result.final_url or url,
                        "domain": domain,
                        "title": title,
                        "text": content,
                        "norm_version": settings.norm_version,
                        "passages": passages,
                        "text_len": len(content),
                        "content_hash": f"sha1:{sha1}",
                        "dup_of": None,
                        "fetch": {
                            "status": status,
                            "http_status": result.http_status,
                            "fetched_at": result.fetched_at,
                            "extractor": f"trafilatura@{trafilatura.__version__}",
                            "lang_detected": language,
                            "lang_conf": confidence,
                        },
                        "pubmed": None,
                        "owner": settings.owner,
                        "code_commit": settings.code_commit,
                    }
    log = {
        "uid": (
            doc["uid"]
            if doc is not None
            else f"src:{source_id}"
        ),
        "id": source_id,
        "url": url,
        "domain": domain,
        "owner": settings.owner,
        "status": status,
        "http_status": result.http_status,
        "attempt": result.attempts,
        "fetched_at": result.fetched_at,
        "bytes": result.nbytes,
        "final_url": result.final_url,
        "error": result.error,
        "shard": None,
    }
    if doc is not None:
        doc["fetch"]["status"] = status
    return log, doc
