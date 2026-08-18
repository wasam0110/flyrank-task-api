# The Polite Scraper — FlyRank A9

This directory contains the Week 5 A9 scraper. It is intentionally isolated from the existing FastAPI/PostgreSQL/Supabase Task API in the repository root.

## Target classification

The target is [Books to Scrape](https://books.toscrape.com/), a public practice sandbox created for learning web scraping. The scraper processes only the first three catalogue pages and follows the catalogue’s own pagination links to discover the 60 book detail pages. It collects each book’s title, product URL, price, stock availability, rating, description, source catalogue page, and fetch timestamp, then stores validated JSON records.

This scope is appropriate because the site is explicitly intended for scraping practice, the dataset is small, and the scraper does not access accounts, paywalls, blocked content, or personal data. The repository’s assignment notes include a one-time `robots.txt` check. The check was performed against `https://books.toscrape.com/robots.txt` and returned **HTTP 404**, so the result is recorded as **no robots file found** in `output/robots-check.json`. Run `python src/main.py --check-robots` to repeat the check deliberately. **I will not reuse this code on another site without checking its rules and terms first.**

The scraper follows the [Robots Exclusion Protocol, RFC 9309](https://www.rfc-editor.org/rfc/rfc9309), and its ethical boundary is simple: use an official API when one exists, never bypass logins, paywalls, or blocks, and collect only what is needed for the assignment.

## Python lane and installation

The implementation uses Python 3.10 or newer with Requests for HTTP, Beautiful Soup for HTML parsing, and Pydantic for schema validation. The dependencies are isolated in `scraper/requirements.txt` so the existing Task API dependency boundary is unchanged.

From the repository root, enter this folder first:

```
flyrank-task-api/
└── scraper/
```

On Windows PowerShell:

```
cd scraper
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

On macOS/Linux:

```bash
cd scraper
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
```

## Commands

The following commands are run from inside the `scraper` directory. Windows PowerShell uses backslashes; macOS/Linux uses forward slashes.

### Windows PowerShell

```
python -m unittest discover -s tests -v
python src\main.py --check-robots
python src\main.py
python src\main.py
python src\main.py --with-fake-url
python src\main.py --fresh
```

### macOS/Linux

```bash
python -m unittest discover -s tests -v
python src/main.py --check-robots
python src/main.py
python src/main.py
python src/main.py --with-fake-url
python src/main.py --fresh
```

The second normal run demonstrates cache hits and idempotency. The deliberate failure checkpoint adds one made-up URL locally; it does not make extra requests to the real catalogue pages. `--fresh` removes cached HTML before a development rerun.

## Pipeline behavior

The scraper follows the assignment’s deterministic pipeline: classify, fetch, cache, discover, extract, normalize, validate, store, and report. The catalogue’s own `next` link is followed until exactly three catalogue pages have been processed; the code does not hardcode the 60 product URLs.

Every real request sends the identifying user-agent `FlyRankInternship-A9/1.0 (+https://github.com/wasam0110/flyrank-task-api )`, uses a timeout, checks the response status before parsing, and waits at least 500 milliseconds between requests. Successful pages are cached under `cache/`; development reruns read the saved HTML instead of repeatedly contacting the site. HTTP 5xx and request errors receive one retry. HTTP 403 and 404 responses are not retried.

Each book is processed independently. A failed or malformed page is recorded in `output/errors.json` and skipped, allowing the remaining good records to finish. The output files are overwritten on each run, records are sorted by canonical product URL, and duplicate URLs are removed before detail-page processing. These choices make reruns idempotent: a second run still produces one record per book rather than appending duplicates.

## Validated record schema

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `title` | string | Yes | Book title from the product area |
| `product_url` | HTTPS URL string | Yes | Canonical absolute product URL |
| `price_text` | string | Yes | Original price text, such as `£51.77` |
| `price_gbp` | number | Yes | Normalized numeric price |
| `availability_text` | string | Yes | Original stock text |
| `rating_text` | string | Yes | Rating text, such as `Three` |
| `description` | string or null | No | Description when present; never invented |
| `source_page` | HTTPS URL string | Yes | Catalogue page that discovered the book |
| `fetched_at` | ISO 8601 string | Yes | Timestamp associated with the cached/fetched page |

Records that fail normalization or Pydantic validation are kept out of `books.json` and written to `errors.json` with the URL, stage, reason, and timestamp.

## Output files

| File | Purpose |
| --- | --- |
| `output/books.json` | Validated, normalized book records; a clean run should contain exactly 60 records |
| `output/errors.json` | Fetch, extraction, or validation failures and their reasons |
| `output/run-report.json` | Counts for pages, cache hits, retries, valid/invalid records, failures, and duration |
| `output/robots-check.json` | The one-time robots.txt check result |
| `cache/*.html` | Local development cache; ignored by Git |

A normal run produced `catalogue_pages=3 discovered=60 unique_urls=60`, followed by `detail_pages=60 valid_records=60 invalid_records=0 failed_pages=0`. A second run produced the same counts with `cache_hits=63`. The deliberate failure run finished with 60 valid records and one reported failure. Its real `output/run-report.json` was:

```json
{
  "catalogue_pages": 3,
  "discovered_urls": 60,
  "unique_urls": 60,
  "detail_pages": 60,
  "pages_fetched": 0,
  "cache_hits": 63,
  "request_attempts": 1,
  "retries": 0,
  "valid_records": 60,
  "invalid_records": 0,
  "failed_pages": 1,
  "failure_urls": [
    "https://books.toscrape.com/catalogue/does-not-exist_9999/index.html"
  ],
  "error_count": 1
}
```

The deliberate failure run leaves the 60 good records in `books.json` and records the fake URL in `errors.json`.

## Why no browser is required

The assignment needs no browser because the book data is already present in the HTML returned by the server. Requests and Beautiful Soup can retrieve and parse that server-rendered content directly, while a browser would add startup cost and complexity without improving the core result.

## Honest limitation

This is a small educational scraper for a stable practice sandbox, not a general-purpose crawler. It supports one catalogue traversal, a fixed three-page scope, one retry for transient failures, and filesystem caching. Production use would require site-specific policy review, richer retry/backoff rules, structured logs, monitoring, and possibly discovery of data delivered through JavaScript or JSON endpoints.

## Assignment checkpoints

Run the following sequence before committing:

```
python -m unittest discover -s tests -v
python src\main.py --check-robots
python src\main.py
python src\main.py
python src\main.py --with-fake-url
```

A successful submission should show seven passing tests, three catalogue pages, 60 unique URLs, 60 valid records, cache hits on the second normal run, and one isolated 404 failure in the deliberate checkpoint.

| Checkpoint | Verification |
| --- | --- |
| Target classification | This README documents the sandbox, scope, data, robots check, and reuse restriction |
| Fetch and cache | First run prints `FETCH`; later development runs print `CACHE HIT` |
| Catalogue discovery | The command reports three pages and 60 unique URLs |
| Raw extraction | The first raw record contains all eight raw fields, including a nullable description |
| Normalization and validation | `books.json` contains numeric `price_gbp` values and HTTPS URLs |
| Failure isolation | `--with-fake-url` completes and records the failed page without stopping the run |
| Reporting | `run-report.json` records counts, failures, cache hits, retries, and duration |
| Tests | Seven offline unit tests cover normalization, URL resolution, parsing, missing descriptions, duplicates, schema output, and malformed HTML |

## Submission structure

Keep this README inside the separate `scraper/` folder. Keep the original project README at the repository root; the root README should only contain a short link and summary for A9.

```
flyrank-task-api/
├── README.md
├── main.py
├── db.py
└── scraper/
    ├── README.md
    ├── .gitignore
    ├── requirements.txt
    ├── src/
    │   ├── __init__.py
    │   ├── main.py
    │   └── scraper.py
    ├── tests/
    │   ├── __init__.py
    │   └── test_scraper.py
    ├── cache/
    └── output/
```

Do not put the scraper code in the root `main.py`, and do not replace the existing Task API README. The A9 README is the detailed documentation for this module.

## Files

```
scraper/
├── README.md
├── .gitignore
├── requirements.txt
├── src/
│   ├── __init__.py
│   ├── main.py
│   └── scraper.py
├── tests/
│   ├── __init__.py
│   └── test_scraper.py
├── cache/
└── output/
```