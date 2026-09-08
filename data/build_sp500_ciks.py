"""Rebuild data/sp500_ciks.json with the full current S&P 500 constituents.

Joins a public S&P 500 constituents list (ticker + name) against SEC's official
ticker -> CIK map (https://www.sec.gov/files/company_tickers.json).

Usage:
    python data/build_sp500_ciks.py
    python data/build_sp500_ciks.py --constituents path/to/constituents.csv

Requires SEC_USER_AGENT to be set (see .env.example).
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import json
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from agents.config import settings  # noqa: E402
from agents.sec_client import SecClient  # noqa: E402

CONSTITUENTS_URL = (
    "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/main/"
    "data/constituents.csv"
)
SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
OUT_PATH = Path(__file__).resolve().parent / "sp500_ciks.json"


def load_constituents(path: str | None) -> list[dict]:
    if path:
        text = Path(path).read_text(encoding="utf-8")
    else:
        print(f"fetching {CONSTITUENTS_URL}")
        resp = requests.get(CONSTITUENTS_URL, timeout=30)
        resp.raise_for_status()
        text = resp.text
    rows = list(csv.DictReader(io.StringIO(text)))
    out = []
    for r in rows:
        symbol = (r.get("Symbol") or r.get("symbol") or "").strip()
        name = (r.get("Security") or r.get("Name") or r.get("name") or "").strip()
        if symbol:
            out.append({"ticker": symbol, "name": name})
    return out


def load_sec_ticker_map(client: SecClient) -> dict[str, int]:
    print(f"fetching {SEC_TICKERS_URL}")
    data = client.get_json(SEC_TICKERS_URL)
    rows = data.values() if isinstance(data, dict) else data
    return {str(row["ticker"]).upper(): int(row["cik_str"]) for row in rows}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--constituents", help="local constituents CSV (Symbol,Security)")
    args = p.parse_args(argv)

    settings.validate_for_fetch()
    client = SecClient()

    constituents = load_constituents(args.constituents)
    sec_map = load_sec_ticker_map(client)

    companies, missing = [], []
    for c in constituents:
        # SEC uses '-' for share classes (BRK-B); lists often use '.' (BRK.B).
        for key in (c["ticker"].upper(), c["ticker"].upper().replace(".", "-")):
            if key in sec_map:
                companies.append(
                    {"ticker": c["ticker"], "name": c["name"], "cik": sec_map[key]}
                )
                break
        else:
            missing.append(c["ticker"])

    companies.sort(key=lambda x: x["ticker"])
    OUT_PATH.write_text(
        json.dumps(
            {
                "_note": "Full S&P 500 constituent -> CIK map. Rebuild with data/build_sp500_ciks.py.",
                "_source": CONSTITUENTS_URL,
                "_updated": dt.date.today().isoformat(),
                "companies": companies,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"wrote {len(companies)} companies -> {OUT_PATH}")
    if missing:
        print(f"WARNING: no CIK found for {len(missing)}: {', '.join(sorted(missing))}",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
