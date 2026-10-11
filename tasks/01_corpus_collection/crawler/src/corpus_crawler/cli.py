from __future__ import annotations

import argparse
import asyncio
from dataclasses import replace
from pathlib import Path

from .engine import run_crawl
from .output import ShardWriter
from .settings import load_settings
from .state import CrawlState
from .source import profile_domains
from .state import DOMAIN_WARMUP_SAMPLES
from .validation import validate_shard_file


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Respectful member-A corpus crawler")
    subparsers = parser.add_subparsers(dest="command", required=True)
    profile = subparsers.add_parser("profile", help="Profile all source domains")
    profile.add_argument("--input", type=Path)
    run = subparsers.add_parser("run", help="Crawl/resume member A's assigned URLs")
    run.add_argument("--input", type=Path)
    run.add_argument(
        "--limit",
        type=int,
        help="Only register the first N URLs assigned to member A (smoke test)",
    )
    subparsers.add_parser("status", help="Show saved progress")
    validate = subparsers.add_parser("validate", help="Validate a completed docs shard")
    validate.add_argument("shard", type=Path)
    return parser


def main() -> None:
    args = _parser().parse_args()
    settings = load_settings()
    if getattr(args, "input", None) is not None:
        settings = replace(settings, input_parquet=args.input.resolve())
    if args.command in {"run", "profile"} and not settings.input_parquet.is_file():
        raise FileNotFoundError(f"Input Parquet not found: {settings.input_parquet}")

    if args.command == "validate":
        shard = args.shard.resolve()
        manifest = (
            settings.corpus_root
            / "viz"
            / "manifest"
            / settings.owner
            / f"{shard.name}.manifest.json"
        )
        count, _ = validate_shard_file(shard, settings.owner, manifest)
        print(f"Valid shard: {shard.name} ({count:,} documents)")
        return

    if args.command == "profile":
        output = settings.corpus_root / "viz" / "input" / "domain_profile.parquet"
        profile_domains(settings.input_parquet, output)
        return

    state = CrawlState(settings.corpus_root / "viz" / "state-a.sqlite3")
    try:
        if args.command == "status":
            total, done, pending = state.totals()
            if not state.has_registered_urls():
                print("No crawl state yet. Start with `python -m corpus_crawler run`.")
                return
            eligible_total, eligible_done, eligible_pending = state.totals(
                settings.excluded_domains
            )
            excluded_pending = pending - eligible_pending
            print(
                f"Owner A: total={total:,}, completed={done:,}, remaining={pending:,}; "
                f"eligible={eligible_done:,}/{eligible_total:,}, "
                f"eligible remaining={eligible_pending:,}, "
                f"excluded pending={excluded_pending:,}"
            )
            performance = [
                row
                for row in state.domain_performance()
                if row["domain"] not in settings.excluded_domains
            ]
            ranked_domains = [
                row
                for row in performance
                if row["sample_count"] >= DOMAIN_WARMUP_SAMPLES
            ]
            calibrating_domains = [
                row
                for row in performance
                if row["sample_count"] < DOMAIN_WARMUP_SAMPLES
            ]
            if ranked_domains:
                print("Stable-domain priority (estimated successful URLs/s):")
                for row in ranked_domains[:10]:
                    print(
                        f"  {row['domain']}: {row['conservative_rate']:.3f} URL/s "
                        f"(n={row['sample_count']}, "
                        f"success={row['success_rate']:.0%}, "
                        f"mean={row['mean_seconds']:.2f}s, "
                        f"sd={row['standard_deviation']:.2f}s)"
                    )
            if calibrating_domains:
                domains = ", ".join(
                    f"{row['domain']} ({row['sample_count']}/{DOMAIN_WARMUP_SAMPLES})"
                    for row in calibrating_domains[:10]
                )
                remainder = len(calibrating_domains) - 10
                if remainder > 0:
                    domains += f", and {remainder} more"
                print(f"Calibrating domains: {domains}")
            if settings.excluded_domains:
                print(f"Excluded domains: {', '.join(sorted(settings.excluded_domains))}")
            print(f"Status counts: {state.completed_counts()}")
            return

        added, scanned = state.prepare_source(settings, args.limit)
        total, done, pending = state.totals()
        eligible_total, eligible_done, eligible_pending = state.totals(
            settings.excluded_domains
        )
        excluded_pending = pending - eligible_pending
        print(
            f"Source rows scanned: {scanned:,}; new assigned URLs: {added:,}; "
            f"registered={total:,}; already complete={done:,}; "
            f"eligible={eligible_done:,}/{eligible_total:,}; "
            f"eligible remaining={eligible_pending:,}; "
            f"excluded pending={excluded_pending:,}"
        )
        if settings.excluded_domains:
            print(f"Excluded domains: {', '.join(sorted(settings.excluded_domains))}")
        writer = ShardWriter(settings, state)
        try:
            asyncio.run(run_crawl(settings, state, writer))
        except KeyboardInterrupt:
            writer.export_ready(force=True)
            print("\nStopped by user; completed results are checkpointed.")
    finally:
        state.close()


if __name__ == "__main__":
    main()
