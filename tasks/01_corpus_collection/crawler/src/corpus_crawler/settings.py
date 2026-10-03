from __future__ import annotations

import tomllib
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


CRAWLER_ROOT = Path(__file__).resolve().parents[2]
REPOSITORY_ROOT = CRAWLER_ROOT.parents[2]


def _git_code_commit() -> str:
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=REPOSITORY_ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain", "--", "tasks/01_corpus_collection/crawler"],
            cwd=REPOSITORY_ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return "uncommitted"
    return f"{commit}-dirty" if dirty else commit


@dataclass(frozen=True)
class Settings:
    owner: str
    schema_version: str
    norm_version: str
    input_parquet: Path
    corpus_root: Path
    global_concurrency: int
    per_domain_concurrency: int
    requests_per_domain: float
    timeout_seconds: int
    max_response_bytes: int
    max_retries: int
    retry_backoff_seconds: float
    min_text_chars: int
    shard_docs: int
    progress_seconds: int
    user_agent: str
    code_commit: str
    domains: frozenset[str]


def load_settings(config_path: Path | None = None) -> Settings:
    config_file = config_path or CRAWLER_ROOT / "config.toml"
    with config_file.open("rb") as stream:
        raw: dict[str, Any] = tomllib.load(stream)
    crawl = raw["crawl"]
    owner = str(crawl["owner"])
    if owner != "a":
        raise ValueError("This crawler is restricted to member A (owner='a').")

    input_path = Path(crawl["input_parquet"])
    if not input_path.is_absolute():
        input_path = REPOSITORY_ROOT / input_path
    domain_file = CRAWLER_ROOT / "domains_a.txt"
    domains = frozenset(
        line.strip().lower()
        for line in domain_file.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )
    if not domains:
        raise ValueError(f"No domains found in {domain_file}")

    settings = Settings(
        owner=owner,
        schema_version=str(crawl["schema_version"]),
        norm_version=str(crawl["norm_version"]),
        input_parquet=input_path,
        corpus_root=REPOSITORY_ROOT / "corpus",
        global_concurrency=int(crawl["global_concurrency"]),
        per_domain_concurrency=int(crawl["per_domain_concurrency"]),
        requests_per_domain=float(crawl["requests_per_domain"]),
        timeout_seconds=int(crawl["timeout_seconds"]),
        max_response_bytes=int(crawl["max_response_bytes"]),
        max_retries=int(crawl["max_retries"]),
        retry_backoff_seconds=float(crawl["retry_backoff_seconds"]),
        min_text_chars=int(crawl["min_text_chars"]),
        shard_docs=int(crawl["shard_docs"]),
        progress_seconds=int(crawl["progress_seconds"]),
        user_agent=str(crawl["user_agent"]),
        code_commit=_git_code_commit(),
        domains=domains,
    )
    if (
        settings.global_concurrency < 1
        or settings.per_domain_concurrency != 1
        or settings.requests_per_domain <= 0
        or settings.timeout_seconds < 1
        or settings.max_response_bytes < 1
        or settings.max_retries < 0
        or settings.retry_backoff_seconds < 0
        or settings.min_text_chars < 1
        or settings.shard_docs < 1
        or settings.progress_seconds < 1
        or not settings.user_agent.strip()
    ):
        raise ValueError("Invalid crawl limits in config.toml.")
    return settings
