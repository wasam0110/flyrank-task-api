"""Core implementation for the Week 5 A9 polite scraper.

The module deliberately keeps network access, parsing, normalization, and output
logic separate from the existing FastAPI application in the repository root.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Callable, Iterable, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, ValidationError

BASE_URL = "https://books.toscrape.com/"
ROBOTS_URL = urljoin(BASE_URL, "robots.txt")
DEFAULT_USER_AGENT = (
    "FlyRankInternship-A9/1.0 (+https://github.com/wasam0110/flyrank-task-api)"
)


class FetchError(RuntimeError):
    """Raised when a page cannot be fetched successfully."""

    def __init__(self, url: str, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.url = url
        self.status_code = status_code


class BookRecord(BaseModel):
    """Validated normalized record stored in output/books.json."""

    title: str
    product_url: str
    price_text: str
    price_gbp: float
    availability_text: str
    rating_text: str
    description: Optional[str] = None
    source_page: str
    fetched_at: str

    class Config:
        extra = "forbid"


@dataclass
class ScraperConfig:
    base_url: str = BASE_URL
    cache_dir: Path = Path("cache")
    output_dir: Path = Path("output")
    user_agent: str = DEFAULT_USER_AGENT
    timeout_seconds: float = 10.0
    delay_seconds: float = 0.5
    max_retries: int = 1
    verbose: bool = True


@dataclass
class RunStats:
    started_at: str
    pages_fetched: int = 0
    cache_hits: int = 0
    request_attempts: int = 0
    retries: int = 0
    catalogue_pages: int = 0
    discovered_urls: int = 0
    unique_urls: int = 0
    detail_pages: int = 0
    valid_records: int = 0
    invalid_records: int = 0
    failed_pages: int = 0
    failure_urls: list[str] = field(default_factory=list)


@dataclass
class FetchResult:
    url: str
    text: str
    status_code: int
    from_cache: bool
    fetched_at: str


class PoliteFetcher:
    """HTTP client that identifies itself, delays requests, caches successes, and retries safely."""

    def __init__(self, config: ScraperConfig, stats: RunStats):
        self.config = config
        self.stats = stats
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": config.user_agent})
        self._last_request_at: Optional[float] = None

    def _log(self, message: str) -> None:
        if self.config.verbose:
            print(message)

    def cache_path(self, url: str) -> Path:
        """Return stable, human-readable cache paths for catalogue pages and books."""
        parsed = urlparse(url)
        path = parsed.path.rstrip("/")
        if url.rstrip("/") == self.config.base_url.rstrip("/"):
            return self.config.cache_dir / "catalogue-page-1.html"
        match = re.search(r"/catalogue/page-(\d+)\.html$", path)
        if match:
            return self.config.cache_dir / f"catalogue-page-{match.group(1)}.html"
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
        return self.config.cache_dir / f"book-{digest}.html"

    def _wait_if_needed(self) -> None:
        if self._last_request_at is None:
            return
        elapsed = time.monotonic() - self._last_request_at
        remaining = self.config.delay_seconds - elapsed
        if remaining > 0:
            time.sleep(remaining)

    def _request_once(self, url: str) -> requests.Response:
        self._wait_if_needed()
        self._last_request_at = time.monotonic()
        self.stats.request_attempts += 1
        return self.session.get(url, timeout=self.config.timeout_seconds)

    def fetch(self, url: str, *, use_cache: bool = True) -> FetchResult:
        """Fetch one URL, using cache when available and retrying only transient failures."""
        cache_path = self.cache_path(url)
        if use_cache and cache_path.exists():
            text = cache_path.read_text(encoding="utf-8")
            fetched_at = datetime.fromtimestamp(
                cache_path.stat().st_mtime, tz=timezone.utc
            ).isoformat().replace("+00:00", "Z")
            self.stats.cache_hits += 1
            self._log(f"CACHE HIT {url} bytes={len(text.encode('utf-8'))}")
            return FetchResult(url, text, 200, True, fetched_at)

        attempts = 0
        while True:
            attempts += 1
            try:
                response = self._request_once(url)
            except requests.RequestException as exc:
                if attempts <= self.config.max_retries:
                    self.stats.retries += 1
                    self._log(f"RETRY {url} reason={type(exc).__name__}")
                    continue
                raise FetchError(url, f"request failed: {exc}") from exc

            status = response.status_code
            if status == 200:
                # Books to Scrape serves UTF-8 HTML without a reliable charset
                # header; decoding response.content explicitly avoids mojibake
                # such as ``Â£`` in the preserved raw price text.
                try:
                    text = response.content.decode("utf-8")
                except UnicodeDecodeError:
                    text = response.text
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                cache_path.write_text(text, encoding="utf-8")
                fetched_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                self.stats.pages_fetched += 1
                self._log(f"FETCH {url} status=200 bytes={len(response.content)}")
                return FetchResult(url, text, status, False, fetched_at)

            # A 403 or 404 is a definitive response and must never be retried.
            if status in {403, 404}:
                raise FetchError(url, f"HTTP {status}", status_code=status)

            # Retry server errors once, as required by the assignment.
            if 500 <= status <= 599 and attempts <= self.config.max_retries:
                self.stats.retries += 1
                self._log(f"RETRY {url} status={status}")
                continue

            raise FetchError(url, f"HTTP {status}", status_code=status)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def normalize_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    cleaned = " ".join(value.split())
    return cleaned or None


def normalize_price(price_text: str) -> float:
    """Convert a pound-denominated string such as ``£51.77`` into a number."""
    match = re.search(r"\d+(?:,\d{3})*(?:\.\d+)?", price_text or "")
    if not match:
        raise ValueError(f"could not parse price: {price_text!r}")
    try:
        return float(Decimal(match.group(0).replace(",", "")))
    except InvalidOperation as exc:
        raise ValueError(f"could not parse price: {price_text!r}") from exc


def absolute_url(href: str, page_url: str) -> str:
    """Resolve a relative link with URL tools and require HTTPS output."""
    result = urljoin(page_url, href)
    if not result.startswith("https://"):
        raise ValueError(f"expected an HTTPS URL, got {result!r}")
    return result


def deduplicate_urls(urls: Iterable[str]) -> list[str]:
    """Remove duplicate URLs while preserving discovery order."""
    seen: set[str] = set()
    unique: list[str] = []
    for url in urls:
        if url not in seen:
            seen.add(url)
            unique.append(url)
    return unique


def parse_catalogue_page(html: str, page_url: str) -> tuple[list[str], Optional[str]]:
    """Extract product links and the catalogue's own next link from one page."""
    soup = BeautifulSoup(html, "html.parser")
    links: list[str] = []
    for anchor in soup.select("article.product_pod h3 a[href]"):
        links.append(absolute_url(anchor["href"], page_url))
    next_anchor = soup.select_one("li.next a[href]")
    next_url = absolute_url(next_anchor["href"], page_url) if next_anchor else None
    return links, next_url


def extract_raw_record(
    html: str, product_url: str, source_page: str, fetched_at: str
) -> dict:
    """Extract the eight raw fields from the product area of a book page."""
    soup = BeautifulSoup(html, "html.parser")
    product = soup.select_one("div.product_main")
    if product is None:
        raise ValueError("product area not found")

    title_node = product.select_one("h1")
    price_node = product.select_one("p.price_color")
    availability_node = product.select_one("p.instock.availability")
    rating_node = product.select_one("p.star-rating")
    description_heading = soup.select_one("#product_description")

    if not title_node or not price_node or not availability_node or not rating_node:
        raise ValueError("required product field missing")

    rating_classes = rating_node.get("class", []) if rating_node else []
    rating_text = next(
        (name for name in rating_classes if name != "star-rating"),
        normalize_text(rating_node.get_text(" ", strip=True)) if rating_node else None,
    )

    description = None
    if description_heading:
        description_node = description_heading.find_next_sibling("p")
        if description_node:
            description = normalize_text(description_node.get_text(" ", strip=True))

    return {
        "title": normalize_text(title_node.get_text(" ", strip=True)) or "",
        "product_url": product_url,
        "price_text": normalize_text(price_node.get_text(" ", strip=True)) or "",
        "availability_text": normalize_text(availability_node.get_text(" ", strip=True)) or "",
        "rating_text": normalize_text(rating_text) or "",
        "description": description,
        "source_page": source_page,
        "fetched_at": fetched_at,
    }


def make_normalized_record(raw: dict) -> dict:
    """Add the clean numeric price and validate the complete schema."""
    normalized = {**raw, "price_gbp": normalize_price(raw["price_text"])}
    if not normalized["product_url"].startswith("https://"):
        raise ValueError("product_url must start with https://")
    if not normalized["source_page"].startswith("https://"):
        raise ValueError("source_page must start with https://")

    try:
        if hasattr(BookRecord, "model_validate"):
            record = BookRecord.model_validate(normalized)
            return record.model_dump()
        record = BookRecord.parse_obj(normalized)
        return record.dict()
    except ValidationError:
        raise


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def check_robots(config: ScraperConfig) -> dict:
    """Request robots.txt once and persist an honest classification result."""
    stats = RunStats(started_at=now_iso())
    fetcher = PoliteFetcher(config, stats)
    checked_at = now_iso()
    try:
        result = fetcher.fetch(ROBOTS_URL, use_cache=False)
        payload = {
            "url": ROBOTS_URL,
            "status_code": result.status_code,
            "result": "robots file found",
            "checked_at": checked_at,
            "excerpt": result.text[:1000],
        }
    except FetchError as exc:
        payload = {
            "url": ROBOTS_URL,
            "status_code": exc.status_code,
            "result": "no robots file found" if exc.status_code == 404 else "request failed",
            "checked_at": checked_at,
            "error": str(exc),
        }
    write_json(config.output_dir / "robots-check.json", payload)
    return payload


def discover_catalogue(
    fetcher: PoliteFetcher, config: ScraperConfig
) -> tuple[list[str], dict[str, str], int]:
    """Follow catalogue next links for exactly the first three catalogue pages."""
    current_url = config.base_url
    all_urls: list[str] = []
    source_pages: dict[str, str] = {}
    catalogue_pages = 0

    while current_url and catalogue_pages < 3:
        result = fetcher.fetch(current_url)
        page_urls, next_url = parse_catalogue_page(result.text, current_url)
        catalogue_pages += 1
        for url in page_urls:
            all_urls.append(url)
            source_pages.setdefault(url, current_url)
        current_url = next_url

    unique_urls = deduplicate_urls(all_urls)
    return unique_urls, source_pages, catalogue_pages


def run_scraper(
    config: Optional[ScraperConfig] = None,
    *,
    include_fake_url: bool = False,
) -> dict:
    """Run the complete deterministic pipeline and write all assignment outputs."""
    config = config or ScraperConfig()
    config.cache_dir.mkdir(parents=True, exist_ok=True)
    config.output_dir.mkdir(parents=True, exist_ok=True)
    started_at = now_iso()
    start_clock = time.monotonic()
    stats = RunStats(started_at=started_at)
    fetcher = PoliteFetcher(config, stats)
    errors: list[dict] = []

    try:
        urls, source_pages, catalogue_pages = discover_catalogue(fetcher, config)
        stats.catalogue_pages = catalogue_pages
        stats.discovered_urls = len(urls)
        stats.unique_urls = len(urls)
        print(
            f"catalogue_pages={catalogue_pages} discovered={len(urls)} unique_urls={len(urls)}"
        )

        detail_urls = list(urls)
        if include_fake_url:
            fake_url = urljoin(config.base_url, "catalogue/does-not-exist_9999/index.html")
            detail_urls.append(fake_url)
            source_pages[fake_url] = config.base_url

        records: list[dict] = []
        first_raw: Optional[dict] = None
        for product_url in detail_urls:
            source_page = source_pages.get(product_url, config.base_url)
            try:
                result = fetcher.fetch(product_url)
                raw = extract_raw_record(
                    result.text,
                    product_url,
                    source_page,
                    result.fetched_at,
                )
                if first_raw is None:
                    first_raw = raw
                try:
                    records.append(make_normalized_record(raw))
                    stats.valid_records += 1
                except (ValidationError, ValueError) as exc:
                    stats.invalid_records += 1
                    errors.append(
                        {
                            "url": product_url,
                            "stage": "validation",
                            "error": str(exc),
                            "status_code": None,
                            "record": raw,
                            "timestamp": now_iso(),
                        }
                    )
            except FetchError as exc:
                stats.failed_pages += 1
                stats.failure_urls.append(product_url)
                errors.append(
                    {
                        "url": product_url,
                        "stage": "fetch",
                        "error": str(exc),
                        "status_code": exc.status_code,
                        "timestamp": now_iso(),
                    }
                )
            except (ValueError, KeyError) as exc:
                stats.invalid_records += 1
                stats.failure_urls.append(product_url)
                errors.append(
                    {
                        "url": product_url,
                        "stage": "extraction",
                        "error": str(exc),
                        "status_code": None,
                        "timestamp": now_iso(),
                    }
                )

        stats.detail_pages = len(detail_urls) - len(stats.failure_urls)
        records.sort(key=lambda record: record["product_url"])
        write_json(config.output_dir / "books.json", records)
        write_json(config.output_dir / "errors.json", errors)
        if first_raw is not None and config.verbose:
            print("first_raw_record=")
            print(json.dumps(first_raw, indent=2, ensure_ascii=False))
        return _finish_run(config, stats, start_clock, errors)
    except Exception as exc:
        # Preserve a report even if discovery itself fails unexpectedly.
        errors.append(
            {
                "url": config.base_url,
                "stage": "pipeline",
                "error": str(exc),
                "status_code": None,
                "timestamp": now_iso(),
            }
        )
        write_json(config.output_dir / "errors.json", errors)
        return _finish_run(config, stats, start_clock, errors)


def _finish_run(
    config: ScraperConfig,
    stats: RunStats,
    start_clock: float,
    errors: list[dict],
) -> dict:
    finished_at = now_iso()
    report = {
        "started_at": stats.started_at,
        "finished_at": finished_at,
        "duration_seconds": round(time.monotonic() - start_clock, 3),
        "catalogue_pages": stats.catalogue_pages,
        "discovered_urls": stats.discovered_urls,
        "unique_urls": stats.unique_urls,
        "detail_pages": stats.detail_pages,
        "pages_fetched": stats.pages_fetched,
        "cache_hits": stats.cache_hits,
        "request_attempts": stats.request_attempts,
        "retries": stats.retries,
        "valid_records": stats.valid_records,
        "invalid_records": stats.invalid_records,
        "failed_pages": stats.failed_pages,
        "failure_urls": stats.failure_urls,
        "error_count": len(errors),
    }
    write_json(config.output_dir / "run-report.json", report)
    print(
        " ".join(
            [
                f"detail_pages={stats.detail_pages}",
                f"valid_records={stats.valid_records}",
                f"invalid_records={stats.invalid_records}",
                f"failed_pages={stats.failed_pages}",
                f"cache_hits={stats.cache_hits}",
            ]
        )
    )
    return report
