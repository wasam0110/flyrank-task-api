"""Command-line entry point for the A9 polite scraper."""

from __future__ import annotations

import argparse
from pathlib import Path

from scraper import ScraperConfig, check_robots, run_scraper


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Polite Books to Scrape pipeline for FlyRank A9."
    )
    parser.add_argument(
        "--check-robots",
        action="store_true",
        help="Request robots.txt once and write output/robots-check.json.",
    )
    parser.add_argument(
        "--with-fake-url",
        action="store_true",
        help="Add one deliberately invalid product URL to prove failure isolation.",
    )
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Ignore existing cached pages and fetch successful pages again.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress per-page fetch messages and the sample raw record.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Minimum delay in seconds between real requests (default: 0.5).",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    root = Path(__file__).resolve().parents[1]
    config = ScraperConfig(
        cache_dir=root / "cache",
        output_dir=root / "output",
        delay_seconds=max(0.5, args.delay),
        verbose=not args.quiet,
    )

    if args.check_robots:
        result = check_robots(config)
        print(
            f"robots_url={result['url']} status_code={result.get('status_code')} "
            f"result={result['result']}"
        )
        return 0

    if args.fresh:
        # The main fetcher intentionally uses the cache when present. Remove only
        # HTML cache files for an explicit fresh run; leave reports intact.
        for cached in config.cache_dir.glob("*.html"):
            cached.unlink()

    report = run_scraper(config, include_fake_url=args.with_fake_url)
    return 0 if report["failed_pages"] == 0 or args.with_fake_url else 1


if __name__ == "__main__":
    raise SystemExit(main())
