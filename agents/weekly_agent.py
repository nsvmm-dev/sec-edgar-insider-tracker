"""Weekly Top-N summary (spec content template 2).

Ranks the highest-value insider trades among already-published briefs and writes
one ranked-list article to ``site/src/content/weekly/``. Deterministic — no LLM,
no API key: every figure is copied from the briefs' front matter, and the only
prose is a fixed intro line plus the mandatory disclaimer.

    python -m agents.weekly_agent --week-ending 2026-09-12
    python -m agents.weekly_agent                     # week ending today (UTC)
"""
from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

from .articles import actor_from_headline, split_markdown, title_case_company
from .config import DISCLAIMER, settings

DEFAULT_DAYS = 7
DEFAULT_TOP = 10


def _fmt_usd(value: float | int) -> str:
    """'$1.9 million', '$940,000' — same natural style the briefs use."""
    v = float(value)
    if v >= 1_000_000:
        return f"${v / 1_000_000:.1f} million".replace(".0 million", " million")
    return f"${v:,.0f}"


def load_briefs(content_dir: Path) -> list[dict]:
    out = []
    for md in sorted(content_dir.glob("*.md")):
        fm, _ = split_markdown(md.read_text(encoding="utf-8"))
        if not fm.get("title") or not fm.get("date"):
            continue
        fm["slug"] = md.stem
        out.append(fm)
    return out


def select_top(
    briefs: list[dict], start: dt.date, end: dt.date, top: int
) -> list[dict]:
    """Briefs whose transaction date is in (start, end], ranked by value desc."""
    picked = []
    for b in briefs:
        try:
            d = dt.date.fromisoformat(str(b["date"]))
        except (ValueError, KeyError):
            continue
        if not (start <= d <= end):
            continue
        if b.get("total_value") in (None, ""):
            continue  # can't rank a trade with no dollar value
        picked.append(b)
    picked.sort(key=lambda b: float(b["total_value"]), reverse=True)
    return picked[:top]


def _filer_from_title(b: dict) -> str:
    who = actor_from_headline(b.get("title"), b.get("filer")) or "an insider"
    # Multi-reporting-owner filings (PE firms etc.) chain names with " / ";
    # collapse to the first entity for the ranked list.
    if " / " in who:
        who = who.split(" / ")[0].rstrip(", ") + " et al."
    return who


def render_markdown(rows: list[dict], start: dt.date, end: dt.date) -> str:
    title = f"Biggest Insider Trades: {start.isoformat()} to {end.isoformat()}"
    lines = [
        "---",
        f'title: "{title}"',
        f'week_start: "{start.isoformat()}"',
        f'week_end: "{end.isoformat()}"',
        f"count: {len(rows)}",
        f'generated: "{dt.datetime.now(dt.timezone.utc).isoformat()}"',
        "---",
        "",
        f"The {len(rows)} largest S&P 500 insider transactions with a reported "
        f"dollar value, for trades dated {start.isoformat()} through "
        f"{end.isoformat()}, ranked by size. Every figure is from an SEC Form 4 "
        f"filing; follow a link for the full brief.",
        "",
    ]
    for i, b in enumerate(rows, 1):
        who = _filer_from_title(b)
        verb = "bought" if b.get("transaction_type") == "purchase" else "sold"
        ticker = b.get("ticker") or "?"
        company = title_case_company(b.get("company")) or ticker
        amount = _fmt_usd(b["total_value"])
        lines.append(
            f"{i}. **{who}** {verb} {amount} of "
            f"[{company} ({ticker})](/articles/{b['slug']}/) "
            f"stock on {b['date']}."
        )
    lines += ["", "---", "", DISCLAIMER, ""]
    return "\n".join(lines)


def run(
    week_ending: str | None = None,
    days: int = DEFAULT_DAYS,
    top: int = DEFAULT_TOP,
    content_dir: Path | None = None,
    out_dir: Path | None = None,
) -> Path | None:
    end = dt.date.fromisoformat(week_ending) if week_ending else dt.date.today()
    start = end - dt.timedelta(days=days - 1)

    briefs_dir = content_dir or settings.site_content_dir
    weekly_dir = out_dir or (briefs_dir.parent / "weekly")
    weekly_dir.mkdir(parents=True, exist_ok=True)

    rows = select_top(load_briefs(briefs_dir), start, end, top)
    if not rows:
        print(f"[weekly] no ranked trades for {start}..{end} — nothing written")
        return None

    out_path = weekly_dir / f"weekly-{end.isoformat()}.md"
    out_path.write_text(render_markdown(rows, start, end), encoding="utf-8")
    print(f"[weekly] {len(rows)} trades ranked -> {out_path}")
    return out_path


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Build the weekly Top-N insider-trade summary.")
    p.add_argument("--week-ending", help="YYYY-MM-DD (default: today UTC)")
    p.add_argument("--days", type=int, default=DEFAULT_DAYS)
    p.add_argument("--top", type=int, default=DEFAULT_TOP)
    args = p.parse_args(argv)
    run(week_ending=args.week_ending or None, days=args.days, top=args.top)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
