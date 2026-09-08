"""Agent (6): weekly newsletter draft (Phase 3).

Summarises the articles published in a date range into a Beehiiv-ready weekly
digest. Draft only — sending stays manual until the Beehiiv Max plan is in place
(spec section 4, (6)).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

from .config import DISCLAIMER, settings
from .llm import complete_text

SYSTEM = """\
You write a weekly email digest for retail investors summarising newly published
briefs about SEC Form 4 insider transactions.

Rules:
- Neutral and factual. No investment advice, no price predictions, no hype.
- Open with one short intro sentence.
- Then a bullet list, one line per trade: name (role), company (ticker),
  bought/sold, amount, date.
- Close with a one-line note that full briefs are on the site at {{SITE_URL}}.
- Markdown output. Do not add your own disclaimer; one is appended.
"""


def _collect(start: dt.date, end: dt.date) -> list[dict]:
    ledger_path = settings.published_index_path
    if not ledger_path.exists():
        return []
    published = json.loads(ledger_path.read_text(encoding="utf-8"))["published"]
    items = []
    for source_url, entry in published.items():
        fd = entry.get("filing_date")
        try:
            d = dt.date.fromisoformat(fd) if fd else None
        except ValueError:
            d = None
        if d and start <= d <= end:
            items.append({"source_url": source_url, **entry})
    return sorted(items, key=lambda e: e.get("filing_date") or "")


def run(week_ending: str, days: int = 7, output_dir: Path | None = None) -> Path:
    settings.validate_for_llm()
    end = dt.date.fromisoformat(week_ending)
    start = end - dt.timedelta(days=days - 1)
    items = _collect(start, end)

    out_dir = (output_dir or settings.output_dir) / "newsletter"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"weekly-{end.isoformat()}.md"

    if not items:
        out_path.write_text(
            f"# Weekly Insider Trades — {start} to {end}\n\n"
            "_No articles were published in this period._\n",
            encoding="utf-8",
        )
        print(f"[newsletter] no items for {start}..{end} -> {out_path}")
        return out_path

    prompt = (
        f"Week: {start} to {end}\nPublished articles (JSON):\n```json\n"
        + json.dumps(items, indent=2, ensure_ascii=False)
        + "\n```"
    )
    body = complete_text(SYSTEM, prompt, max_tokens=3000)
    md = (
        f"---\ntype: weekly-digest\nweek_start: \"{start}\"\nweek_end: \"{end}\"\n"
        f"status: draft\n---\n\n{body.strip()}\n\n---\n\n{DISCLAIMER}\n"
    )
    out_path.write_text(md, encoding="utf-8")
    print(f"[newsletter] draft for {start}..{end} ({len(items)} items) -> {out_path}")
    return out_path


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Draft the weekly newsletter digest.")
    p.add_argument("--week-ending", required=True, help="YYYY-MM-DD (usually Friday)")
    p.add_argument("--days", type=int, default=7)
    args = p.parse_args(argv)
    run(args.week_ending, days=args.days)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
