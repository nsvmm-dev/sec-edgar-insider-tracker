"""Tests for agents/articles.py. Run with pytest or `python tests/test_articles.py`."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.articles import (  # noqa: E402
    article_slug,
    build_markdown,
    slugify,
    split_markdown,
)

RECORD = {
    "transaction_date": "2026-09-04",
    "company_ticker": "AAPL",
    "transaction_type": "sale",
    "source_url": "https://www.sec.gov/Archives/edgar/data/320193/x/y-index.htm",
}


def test_slugify_collapses_and_trims():
    assert slugify("Hello, World!") == "hello-world"
    assert slugify("2026-09-04", "AAPL", "sale") == "2026-09-04-aapl-sale"
    assert slugify("", None, "x") == "x"


def test_article_slug_is_deterministic_and_shaped():
    a = article_slug(RECORD)
    b = article_slug(dict(RECORD))
    assert a == b
    # date-ticker-type-<8 hex>
    assert a.startswith("2026-09-04-aapl-sale-")
    digest = a.rsplit("-", 1)[1]
    assert len(digest) == 8 and all(c in "0123456789abcdef" for c in digest)


def test_article_slug_varies_with_source_url():
    other = dict(RECORD, source_url="https://example.test/other")
    assert article_slug(RECORD) != article_slug(other)


def test_article_slug_handles_missing_fields():
    assert article_slug({}).startswith("undated-unknown-trade-")


def test_front_matter_round_trip():
    fm = {
        "title": 'He said "hi"',
        "date": "2026-09-04",
        "shares": 1439,
        "price_per_share": 317.01,
        "total_value": None,
        "flagged": True,
    }
    md = build_markdown(fm, "Body text here.\n")
    parsed, body = split_markdown(md)
    assert body == "Body text here."
    assert parsed["title"] == 'He said "hi"'
    assert parsed["date"] == "2026-09-04"
    assert parsed["shares"] == 1439
    assert parsed["price_per_share"] == 317.01
    assert parsed["total_value"] is None
    assert parsed["flagged"] is True


def test_split_markdown_without_front_matter():
    fm, body = split_markdown("no front matter here")
    assert fm == {}
    assert body == "no front matter here"


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except AssertionError as exc:
            failed += 1
            print(f"FAIL {fn.__name__}: {exc}")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"ERROR {fn.__name__}: {exc!r}")
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(_run_all())
