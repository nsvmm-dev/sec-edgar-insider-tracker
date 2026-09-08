"""Agent (1): data acquisition.

Given a calendar date, collect every S&P 500 open-market insider transaction
(Form 4, codes P/S) filed that day and emit structured JSON matching the schema
in spec section 4.

Two strategies:

* ``submissions`` (default) — walk the S&P 500 CIK list and read each company's
  ``/submissions/CIK*.json`` feed. Bounded at ~500 requests/day regardless of
  market-wide filing volume, and the index already tells us the issuer.
* ``daily-index`` — the flow described in spec section 2: pull that day's
  ``form.idx``, keep Form 4 rows, then fetch each filing to read its issuer CIK
  and match it against the S&P 500 list. Heavier (one request per Form 4 filed
  nationwide) but does not depend on the submissions feed.

Numbers are copied verbatim from the filing; unavailable fields are ``null``;
companies outside the S&P 500 list are discarded (spec section 4, agent (1)).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

from .config import SEC_ARCHIVES_BASE, SEC_DATA_BASE, settings
from .form4_parser import (
    Form4Record,
    extract_ownership_xml,
    filter_form4_rows,
    parse_daily_index,
    parse_form4,
)
from .sec_client import SecClient

OWNERSHIP_FORMS = {"4", "4/A"}


# --------------------------------------------------------------------------- #
# S&P 500 reference list                                                      #
# --------------------------------------------------------------------------- #
def load_sp500(path: Path | None = None) -> list[dict]:
    path = path or settings.sp500_ciks_path
    if not path.exists():
        raise FileNotFoundError(
            f"S&P 500 CIK list not found at {path}. Run data/build_sp500_ciks.py "
            "or start from the bundled seed file."
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    entries = data["companies"] if isinstance(data, dict) else data
    out = []
    for e in entries:
        cik = str(e["cik"]).lstrip("0") or "0"
        out.append({"cik": cik, "ticker": e.get("ticker"), "name": e.get("name")})
    return out


def _padded(cik: str) -> str:
    return cik.zfill(10)


def _accession_nodash(accession: str) -> str:
    return accession.replace("-", "")


def _index_url(cik: str, accession: str) -> str:
    return (
        f"{SEC_ARCHIVES_BASE}/Archives/edgar/data/{int(cik)}/"
        f"{_accession_nodash(accession)}/{accession}-index.htm"
    )


def _submission_txt_url(cik: str, accession: str) -> str:
    return (
        f"{SEC_ARCHIVES_BASE}/Archives/edgar/data/{int(cik)}/"
        f"{_accession_nodash(accession)}/{accession}.txt"
    )


# --------------------------------------------------------------------------- #
# Strategy: submissions feed                                                  #
# --------------------------------------------------------------------------- #
def _iter_recent_form4(feed: dict, target: str):
    recent = feed.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    accessions = recent.get("accessionNumber", [])
    for i, form in enumerate(forms):
        if form in OWNERSHIP_FORMS and dates[i] == target:
            yield accessions[i]


def fetch_via_submissions(
    client: SecClient,
    companies: list[dict],
    target: str,
    limit: int | None,
) -> list[Form4Record]:
    records: list[Form4Record] = []
    seen: set[str] = set()
    for n, co in enumerate(companies, 1):
        if limit and len(records) >= limit:
            break
        feed_url = f"{SEC_DATA_BASE}/submissions/CIK{_padded(co['cik'])}.json"
        try:
            feed = client.get_json(feed_url)
        except Exception as exc:  # noqa: BLE001 - one bad company must not stop the run
            print(f"  ! {co['ticker'] or co['cik']}: submissions fetch failed ({exc})",
                  file=sys.stderr)
            continue

        for accession in _iter_recent_form4(feed, target):
            if accession in seen:
                continue
            seen.add(accession)
            txt_url = _submission_txt_url(co["cik"], accession)
            try:
                submission = client.get_text(txt_url)
            except Exception as exc:  # noqa: BLE001
                print(f"  ! {accession}: filing fetch failed ({exc})", file=sys.stderr)
                continue
            xml = extract_ownership_xml(submission)
            if not xml:
                print(f"  ! {accession}: no ownership XML (pre-2003 format?)",
                      file=sys.stderr)
                continue
            parsed = parse_form4(
                xml,
                source_url=_index_url(co["cik"], accession),
                raw_filing_url=txt_url,
            )
            for rec in parsed:
                rec.accession = accession
                rec.company_name = rec.company_name or co["name"]
                rec.company_ticker = rec.company_ticker or co["ticker"]
                records.append(rec)
        if n % 50 == 0:
            print(f"  ... scanned {n}/{len(companies)} companies, {len(records)} records")
    return records


# --------------------------------------------------------------------------- #
# Strategy: daily index                                                       #
# --------------------------------------------------------------------------- #
def _daily_index_url(date: dt.date) -> str:
    quarter = (date.month - 1) // 3 + 1
    return (
        f"{SEC_ARCHIVES_BASE}/Archives/edgar/daily-index/{date.year}/"
        f"QTR{quarter}/form.{date:%Y%m%d}.idx"
    )


def fetch_via_daily_index(
    client: SecClient,
    companies: list[dict],
    date: dt.date,
    limit: int | None,
    max_filings: int,
) -> list[Form4Record]:
    sp500_ciks = {co["cik"] for co in companies}
    by_cik = {co["cik"]: co for co in companies}

    idx_text = client.get_text(_daily_index_url(date))
    rows = filter_form4_rows(parse_daily_index(idx_text))
    print(f"  {len(rows)} Form 4 filings in the daily index for {date}")
    if len(rows) > max_filings:
        print(f"  (capping at --max-filings={max_filings})")
        rows = rows[:max_filings]

    records: list[Form4Record] = []
    for i, row in enumerate(rows, 1):
        if limit and len(records) >= limit:
            break
        parts = row.file_name.split("/")
        path_cik, accession_txt = parts[2], parts[3]
        accession = accession_txt.removesuffix(".txt")
        txt_url = f"{SEC_ARCHIVES_BASE}/Archives/{row.file_name}"
        try:
            submission = client.get_text(txt_url)
        except Exception as exc:  # noqa: BLE001
            print(f"  ! {accession}: fetch failed ({exc})", file=sys.stderr)
            continue
        xml = extract_ownership_xml(submission)
        if not xml:
            continue
        parsed = parse_form4(
            xml,
            source_url=_index_url(path_cik, accession),
            raw_filing_url=txt_url,
        )
        for rec in parsed:
            if rec.issuer_cik not in sp500_ciks:
                continue  # not an S&P 500 issuer — discard
            co = by_cik.get(rec.issuer_cik, {})
            rec.accession = accession
            rec.company_ticker = rec.company_ticker or co.get("ticker")
            rec.company_name = rec.company_name or co.get("name")
            records.append(rec)
        if i % 200 == 0:
            print(f"  ... {i}/{len(rows)} filings, {len(records)} S&P 500 records")
    return records


# --------------------------------------------------------------------------- #
# Filtering + output                                                          #
# --------------------------------------------------------------------------- #
def apply_value_filter(records: list[Form4Record]) -> list[Form4Record]:
    threshold = settings.min_total_value_usd
    if threshold <= 0:
        return records
    kept = []
    for r in records:
        if r.total_value is None or r.total_value >= threshold:
            kept.append(r)
    dropped = len(records) - len(kept)
    if dropped:
        print(f"  value filter (>= ${threshold:,.0f}): dropped {dropped}, kept {len(kept)}")
    return kept


def run(
    date_str: str | None = None,
    strategy: str = "submissions",
    limit: int | None = None,
    max_filings: int = 4000,
    tickers: list[str] | None = None,
    output_dir: Path | None = None,
) -> Path:
    settings.validate_for_fetch()
    date = (
        dt.date.fromisoformat(date_str)
        if date_str
        else dt.date.today()
    )
    target = date.isoformat()
    client = SecClient()

    companies = load_sp500()
    if tickers:
        want = {t.strip().upper() for t in tickers}
        companies = [c for c in companies if (c["ticker"] or "").upper() in want]
    print(f"[fetch] {target} | strategy={strategy} | {len(companies)} companies")

    if strategy == "submissions":
        records = fetch_via_submissions(client, companies, target, limit)
    elif strategy == "daily-index":
        records = fetch_via_daily_index(client, companies, date, limit, max_filings)
    else:
        raise ValueError(f"unknown strategy: {strategy}")

    records = apply_value_filter(records)
    records.sort(key=lambda r: (r.total_value or 0), reverse=True)

    out_dir = (output_dir or settings.output_dir) / target
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "filings.json"
    payload = {
        "date": target,
        "strategy": strategy,
        "count": len(records),
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "records": [r.to_dict() for r in records],
    }
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[fetch] wrote {len(records)} records -> {out_path}")
    return out_path


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Fetch S&P 500 Form 4 insider trades for a date.")
    p.add_argument("--date", help="YYYY-MM-DD (default: today)")
    p.add_argument(
        "--strategy",
        choices=["submissions", "daily-index"],
        default="submissions",
    )
    p.add_argument("--limit", type=int, help="stop after N records (debugging)")
    p.add_argument("--max-filings", type=int, default=4000,
                   help="daily-index: cap filings inspected")
    p.add_argument("--tickers", help="comma-separated ticker allow-list (debugging)")
    args = p.parse_args(argv)
    run(
        date_str=args.date,
        strategy=args.strategy,
        limit=args.limit,
        max_filings=args.max_filings,
        tickers=args.tickers.split(",") if args.tickers else None,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
