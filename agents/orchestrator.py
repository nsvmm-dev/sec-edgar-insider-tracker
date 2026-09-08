"""Phase 1 pipeline: fetch -> write -> QA -> publish for one calendar date.

Each stage reads the previous stage's output from OUTPUT_DIR/<date>/ so stages
can also be run individually (see each *_agent.py).

Examples:
    python -m agents.orchestrator --date 2026-09-05
    python -m agents.orchestrator --date 2026-09-05 --tickers AAPL,MSFT,NVDA
    python -m agents.orchestrator --date 2026-09-05 --stages fetch,write --limit 3
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
import traceback

from . import fetch_agent, publish_agent, qa_agent, write_agent

ALL_STAGES = ["fetch", "write", "qa", "publish"]


def run(
    date_str: str | None,
    stages: list[str],
    strategy: str = "submissions",
    limit: int | None = None,
    tickers: list[str] | None = None,
    commit: bool = False,
    dry_run_publish: bool = False,
) -> int:
    date_str = date_str or dt.date.today().isoformat()
    print(f"=== pipeline {date_str} :: stages={','.join(stages)} ===")

    try:
        if "fetch" in stages:
            fetch_agent.run(
                date_str=date_str, strategy=strategy, limit=limit, tickers=tickers
            )
        if "write" in stages:
            write_agent.run(date_str, limit=limit)
        if "qa" in stages:
            qa_agent.run(date_str)
        if "publish" in stages:
            publish_agent.run(date_str, commit=commit, dry_run=dry_run_publish)
    except Exception:  # noqa: BLE001 - report and fail with a non-zero code
        traceback.print_exc()
        print("=== pipeline FAILED ===", file=sys.stderr)
        return 1

    print("=== pipeline OK ===")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--date", help="YYYY-MM-DD (default: today)")
    p.add_argument("--stages", default=",".join(ALL_STAGES),
                   help=f"comma list from {ALL_STAGES}")
    p.add_argument("--strategy", choices=["submissions", "daily-index"], default="submissions")
    p.add_argument("--limit", type=int, help="cap records/articles (debugging)")
    p.add_argument("--tickers", help="comma-separated ticker allow-list")
    p.add_argument("--commit", action="store_true", help="git commit published articles")
    p.add_argument("--dry-run-publish", action="store_true")
    args = p.parse_args(argv)

    stages = [s.strip() for s in args.stages.split(",") if s.strip()]
    bad = set(stages) - set(ALL_STAGES)
    if bad:
        p.error(f"unknown stage(s): {', '.join(bad)}")

    return run(
        date_str=args.date,
        stages=stages,
        strategy=args.strategy,
        limit=args.limit,
        tickers=args.tickers.split(",") if args.tickers else None,
        commit=args.commit,
        dry_run_publish=args.dry_run_publish,
    )


if __name__ == "__main__":
    raise SystemExit(main())
