"""Tests for agents/weekly_agent.py. Run with pytest or `python tests/test_weekly_agent.py`."""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.weekly_agent import (  # noqa: E402
    _filer_from_title,
    _fmt_usd,
    render_markdown,
    select_top,
)

BRIEFS = [
    {"title": "A (CEO) Sells $5M", "date": "2026-09-04", "total_value": 5_000_000, "ticker": "AAA", "transaction_type": "sale", "slug": "a", "company": "Alpha Inc"},
    {"title": "B (CFO) Buys $9M", "date": "2026-09-05", "total_value": 9_000_000, "ticker": "BBB", "transaction_type": "purchase", "slug": "b", "company": "Beta Co"},
    {"title": "C sold shares", "date": "2026-09-05", "total_value": None, "ticker": "CCC", "slug": "c", "company": "Gamma"},
    {"title": "D (Dir) Sells $1M", "date": "2026-08-01", "total_value": 1_000_000, "ticker": "DDD", "transaction_type": "sale", "slug": "d", "company": "Delta"},
    {"title": "E (VP) Sells $2M", "date": "2026-09-06", "total_value": 2_000_000, "ticker": "EEE", "transaction_type": "sale", "slug": "e", "company": "Epsilon"},
]


def test_select_top_filters_window_and_null_then_ranks():
    rows = select_top(BRIEFS, dt.date(2026, 8, 31), dt.date(2026, 9, 6), top=10)
    # D is out of window; C has no value; expect B(9M), A(5M), E(2M) in order.
    assert [r["slug"] for r in rows] == ["b", "a", "e"]


def test_select_top_respects_limit():
    rows = select_top(BRIEFS, dt.date(2026, 8, 31), dt.date(2026, 9, 6), top=2)
    assert [r["slug"] for r in rows] == ["b", "a"]


def test_fmt_usd():
    assert _fmt_usd(9_000_000) == "$9 million"
    assert _fmt_usd(1_250_000) == "$1.2 million"
    assert _fmt_usd(940_000) == "$940,000"


def test_filer_from_title():
    assert _filer_from_title({"title": "Jane Doe (CEO) Sells $5M"}) == "Jane Doe"
    assert _filer_from_title({"title": "No parens here", "filer": "RAW NAME"}) == "RAW NAME"


def test_render_markdown_shape():
    rows = select_top(BRIEFS, dt.date(2026, 8, 31), dt.date(2026, 9, 6), top=10)
    md = render_markdown(rows, dt.date(2026, 8, 31), dt.date(2026, 9, 6))
    assert md.startswith("---\n")
    assert 'week_end: "2026-09-06"' in md
    assert "1. **B**" in md and "[Beta Co (BBB)](/articles/b/)" in md
    assert "informational purposes only" in md  # disclaimer present


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
