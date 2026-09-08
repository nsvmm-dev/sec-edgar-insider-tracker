"""Agent (5): social drafts (Phase 3).

Picks the most notable trades from a day's published set (by total value) and
drafts neutral X/Twitter posts. Drafts only — a human posts them until this is
promoted to full automation (spec section 4, (5)).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import settings
from .llm import complete_text

SYSTEM = """\
You write short, neutral posts for X (Twitter) announcing a newly published news
brief about a SEC Form 4 insider transaction.

Rules:
- <= 260 characters, plain and factual.
- No hype or alarm words ("shocking", "huge red flag", "dump", "loading up").
- No investment advice or price predictions.
- State who traded, their role, the company/ticker, buy or sell, and the amount.
- End with the article URL placeholder {{URL}}.
Return only the post text.
"""


def run(date_str: str, top: int = 5, output_dir: Path | None = None) -> Path:
    settings.validate_for_llm()
    base = (output_dir or settings.output_dir) / date_str
    publish_path = base / "publish.json"
    if not publish_path.exists():
        raise FileNotFoundError(f"{publish_path} not found — run the publish agent first.")

    articles = json.loads(publish_path.read_text(encoding="utf-8"))["articles"]
    manifest = {a["slug"]: a for a in json.loads((base / "articles.json").read_text("utf-8"))["articles"]}

    ranked = sorted(
        articles,
        key=lambda a: (manifest.get(a["slug"], {}).get("record", {}).get("total_value") or 0),
        reverse=True,
    )[:top]

    out_dir = base / "social"
    out_dir.mkdir(parents=True, exist_ok=True)
    drafts = []
    for a in ranked:
        record = manifest.get(a["slug"], {}).get("record", {})
        prompt = (
            f"Title: {a.get('title')}\nRecord JSON:\n```json\n"
            + json.dumps(record, indent=2, ensure_ascii=False)
            + "\n```"
        )
        text = complete_text(SYSTEM, prompt, max_tokens=400)
        (out_dir / f"{a['slug']}.txt").write_text(text + "\n", encoding="utf-8")
        drafts.append({"slug": a["slug"], "text": text})
        print(f"  draft: {a['slug']}")

    report = out_dir / "drafts.json"
    report.write_text(
        json.dumps({"date": date_str, "status": "draft", "drafts": drafts},
                   indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"[social] {len(drafts)} drafts (review before posting) -> {report}")
    return report


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Draft social posts for a day's articles.")
    p.add_argument("--date", required=True)
    p.add_argument("--top", type=int, default=5)
    args = p.parse_args(argv)
    run(args.date, top=args.top)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
