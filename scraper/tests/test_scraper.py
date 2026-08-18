from pathlib import Path
import sys
import unittest

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))

from scraper import (  # noqa: E402
    absolute_url,
    deduplicate_urls,
    extract_raw_record,
    make_normalized_record,
    normalize_price,
    parse_catalogue_page,
)


PRODUCT_FIXTURE = """
<html>
  <body>
    <div class="product_main">
      <h1>A Test Book</h1>
      <p class="price_color">£51.77</p>
      <p class="instock availability">In stock (22 available)</p>
      <p class="star-rating Three">Three</p>
    </div>
    <div id="product_description"></div>
    <p> A description with   extra whitespace. </p>
  </body>
</html>
"""


MISSING_DESCRIPTION_FIXTURE = """
<html>
  <body>
    <div class="product_main">
      <h1>A Book Without Description</h1>
      <p class="price_color">£10.00</p>
      <p class="instock availability">In stock</p>
      <p class="star-rating One">One</p>
    </div>
  </body>
</html>
"""


class ScraperUnitTests(unittest.TestCase):
    def test_price_normalization(self):
        self.assertEqual(normalize_price("£1,234.56"), 1234.56)

    def test_relative_url_becomes_absolute_https_url(self):
        result = absolute_url(
            "a-light-in-the-attic_1000/index.html",
            "https://books.toscrape.com/catalogue/page-1.html",
        )
        self.assertEqual(
            result,
            "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
        )

    def test_catalogue_parser_extracts_links_and_next_page(self):
        html = """
        <article class="product_pod"><h3><a href="book-one/index.html">One</a></h3></article>
        <article class="product_pod"><h3><a href="book-two/index.html">Two</a></h3></article>
        <li class="next"><a href="page-2.html">next</a></li>
        """
        links, next_url = parse_catalogue_page(
            html, "https://books.toscrape.com/catalogue/page-1.html"
        )
        self.assertEqual(len(links), 2)
        self.assertEqual(
            next_url, "https://books.toscrape.com/catalogue/page-2.html"
        )

    def test_missing_description_is_none(self):
        raw = extract_raw_record(
            MISSING_DESCRIPTION_FIXTURE,
            "https://books.toscrape.com/catalogue/book/index.html",
            "https://books.toscrape.com/catalogue/page-1.html",
            "2026-08-18T00:00:00Z",
        )
        self.assertIsNone(raw["description"])

    def test_duplicate_urls_are_removed_in_discovery_order(self):
        urls = ["https://example.test/a", "https://example.test/a", "https://example.test/b"]
        self.assertEqual(
            deduplicate_urls(urls),
            ["https://example.test/a", "https://example.test/b"],
        )

    def test_normalized_record_contains_numeric_price(self):
        raw = extract_raw_record(
            PRODUCT_FIXTURE,
            "https://books.toscrape.com/catalogue/test/index.html",
            "https://books.toscrape.com/catalogue/page-1.html",
            "2026-08-18T00:00:00Z",
        )
        record = make_normalized_record(raw)
        self.assertEqual(record["price_text"], "£51.77")
        self.assertEqual(record["price_gbp"], 51.77)
        self.assertEqual(record["rating_text"], "Three")
        self.assertEqual(record["description"], "A description with extra whitespace.")

    def test_malformed_fixture_is_rejected(self):
        with self.assertRaises(ValueError):
            extract_raw_record(
                "<html><body><h1>Not a product</h1></body></html>",
                "https://books.toscrape.com/catalogue/bad/index.html",
                "https://books.toscrape.com/catalogue/page-1.html",
                "2026-08-18T00:00:00Z",
            )


if __name__ == "__main__":
    unittest.main()
