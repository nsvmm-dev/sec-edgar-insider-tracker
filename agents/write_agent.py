"""Agent (2): article writer.

Turns one structured Form 4 record into a 200-400 word plain-English news brief
for retail investors. The mandatory disclaimer is appended by code so it is
always present and byte-exact; the model is told not to write its own.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

from .articles import article_slug, build_markdown
from .config import DISCLAIMER, settings
from .llm import complete_text

SYSTEM = """\
You are a financial news writer for a website read by ordinary US retail
investors (not professionals). You turn a single SEC Form 4 insider-transaction
record into a short, factual news brief.

Hard rules:
- Specific facts — every figure, name, job title, ticker, price and date — must
  come ONLY from the input record. Never introduce a number that is not in the
  data. Do NOT add identifying details that are not in the record even if you
  believe they are true: no stock-exchange names (NYSE/NASDAQ), no market cap,
  no other executives' names, no headquarters, no past-performance figures.
- Paragraph 2 (the company description) may use general knowledge to say, in
  plain terms, what the company does and how it makes money. That is expected.
- Do NOT put any URL in the body. The source link is added by the site template.
- Do NOT speculate about WHY the person traded (tax planning, market outlook,
  diversification, loss of confidence, etc.). State only what the filing shows.
- Do NOT give or imply investment advice. Banned phrasings include "buy now",
  "you should", "this means the stock will rise/fall", "a red flag", "bullish",
  "bearish".
- Neutral tone. No hype words ("shocking", "massive", "huge", "plunge").
- If a value in the record is null, do not mention it or invent it.
- Do NOT write a disclaimer yourself; one is appended automatically.

Length: the body must be between 240 and 340 words. Count the words. A brief
under 220 words or over 360 words is not acceptable.

Output format — return exactly this and nothing else:

TITLE: <headline>
BODY:
<article body in Markdown>

Headline pattern:
  "<Name> (<Title>) <Buys|Sells> $<Amount> in <Company> Stock"
  - Use "Buys" for a purchase, "Sells" for a sale.
  - <Amount> is total_value phrased naturally ("$1.2 million", "$940,000").
  - If total_value is null, use share count instead:
    "<Name> (<Title>) <Buys|Sells> <N> Shares of <Company> Stock".

Body structure (three paragraphs):
  1. The facts: who, their role, the company and ticker, the transaction type,
     share count, price per share, total value, and the transaction date. You
     may add one short clause defining the transaction code (e.g. "code S, an
     open-market sale").
  2. Two to four sentences on what the company does and how it earns revenue,
     at a general level.
  3. One or two sentences stating the data comes from a Form 4 filed with the
     SEC for this issuer. Do not lecture about Form 4 deadlines, reporting
     thresholds, or Forms 3 and 5.
"""


def _render_prompt(record: dict) -> str:
    return (
        "Form 4 record (JSON):\n```json\n"
        + json.dumps(record, indent=2, ensure_ascii=False)
        + "\n```\n\nWrite the brief now."
    )


def _parse_output(raw: str) -> tuple[str, str]:
    title = ""
    body = raw
    if "TITLE:" in raw:
        after = raw.split("TITLE:", 1)[1]
        if "BODY:" in after:
            title_part, body = after.split("BODY:", 1)
            title = title_part.strip()
        else:
            lines = after.strip().splitlines()
            title = lines[0].strip() if lines else ""
            body = "\n".join(lines[1:]).strip()
    return title.strip().strip('"'), body.strip()


def write_article(record: dict) -> tuple[dict, str]:
    raw = complete_text(SYSTEM, _render_prompt(record), max_tokens=2000)
    title, body = _parse_output(raw)
    if not title:
        raise RuntimeError("write agent produced no TITLE")

    body_with_disclaimer = f"{body}\n\n---\n\n{DISCLAIMER}"
    front_matter = {
        "title": title,
        "date": record.get("transaction_date"),
        "company": record.get("company_name"),
        "ticker": record.get("company_ticker"),
        "filer": record.get("filer_name"),
        "filer_title": record.get("filer_title"),
        "transaction_type": record.get("transaction_type"),
        "shares": record.get("shares"),
        "price_per_share": record.get("price_per_share"),
        "total_value": record.get("total_value"),
        "source_url": record.get("source_url"),
        "slug": article_slug(record),
        "template": "insider-trade-brief",
        "generated_by": "write_agent",
    }
    return front_matter, build_markdown(front_matter, body_with_disclaimer)


def run(date_str: str, output_dir: Path | None = None, limit: int | None = None) -> Path:
    settings.validate_for_llm()
    base = (output_dir or settings.output_dir) / date_str
    filings_path = base / "filings.json"
    if not filings_path.exists():
        raise FileNotFoundError(f"{filings_path} not found — run the fetch agent first.")

    records = json.loads(filings_path.read_text(encoding="utf-8"))["records"]
    if limit:
        records = records[:limit]

    art_dir = base / "articles"
    art_dir.mkdir(parents=True, exist_ok=True)
    manifest = []
    for i, record in enumerate(records, 1):
        slug = article_slug(record)
        md_path = art_dir / f"{slug}.md"
        try:
            fm, markdown = write_article(record)
        except Exception as exc:  # noqa: BLE001 - skip the bad one, keep going
            print(f"  ! [{i}/{len(records)}] {slug}: {exc}", file=sys.stderr)
            continue
        md_path.write_text(markdown, encoding="utf-8")
        manifest.append(
            {"slug": slug, "article_path": str(md_path), "record": record,
             "front_matter": fm}
        )
        print(f"  [{i}/{len(records)}] {slug} -> {fm['title']}")

    manifest_path = base / "articles.json"
    manifest_path.write_text(
        json.dumps(
            {"date": date_str, "count": len(manifest),
             "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
             "articles": manifest},
            indent=2, ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"[write] {len(manifest)} articles -> {manifest_path}")
    return manifest_path


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Generate articles from fetched filings.")
    p.add_argument("--date", required=True, help="YYYY-MM-DD (matches the fetch run)")
    p.add_argument("--limit", type=int)
    args = p.parse_args(argv)
    run(args.date, limit=args.limit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
