"""Agent (3): QA / fact-check.

Verifies each generated article against its source record. Runs cheap
deterministic checks first (disclaimer present, no advice phrasings), then asks
the model to fact-check names/figures and flag hallucinations or speculation.

Output per article: {"status": "approved" | "rejected", "issues": [...]}.
An article is approved only if BOTH the deterministic checks and the model
review pass.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path

from .articles import split_markdown
from .config import DISCLAIMER, settings
from .llm import complete_json

_WS = re.compile(r"\s+")
_URL_RE = re.compile(r"https?://", re.IGNORECASE)

# Body length bounds (spec section 3: 200-400 words). A little slack either side
# before the article is rejected for length.
MIN_BODY_WORDS = 200
MAX_BODY_WORDS = 380

# Phrasings that imply a buy/sell recommendation or hype (spec section 4, (3.2)).
BANNED_PATTERNS = [
    r"\bbuy now\b",
    r"\bsell now\b",
    r"\byou should (buy|sell|invest)\b",
    r"\b(will|is going to) (rise|fall|soar|plunge|drop|climb)\b",
    r"\bguaranteed\b",
    r"\bred flag\b",
    r"\b(this|that) means the stock\b",
    r"\bbullish\b",
    r"\bbearish\b",
    r"\bstrong (buy|sell)\b",
    r"\bdon'?t miss\b",
]

REVIEW_SYSTEM = """\
You are a fact-checking editor. You are given a SEC Form 4 record (JSON) and a
draft article. Check, strictly:

1. Facts: every monetary amount, share count, person name, job title, company
   name and ticker in the article matches the record. Approximate wording of
   numbers is fine ("$1.2 million" for 1200000); a different value is not.
2. Advice: the article must not recommend buying/selling or predict the stock
   price.
3. Disclaimer: a disclaimer paragraph is present at the end.
4. Hallucination: the article must not state or imply anything absent from the
   record — especially a REASON for the trade (tax, outlook, confidence, etc.).
5. No outside identifying facts: reject added specifics that are not in the
   record even if true — stock-exchange names (NYSE/NASDAQ), market cap,
   headquarters, other executives' names, past stock performance, or any other
   figure not in the record. A general-knowledge description of what the company
   does and how it makes money (roughly one short paragraph) is expected and
   fine; a one-clause definition of the transaction code is also fine.
6. Scope: reject a multi-sentence lecture about Form 4 deadlines, reporting
   thresholds, or Forms 3/5. A brief mention that the data is from a Form 4 is
   fine.

Return JSON: {"status": "approved" | "rejected", "issues": [short strings]}.
Reject if any check fails. "issues" must be empty when status is "approved".
"""

REVIEW_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {"type": "string", "enum": ["approved", "rejected"]},
        "issues": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["status", "issues"],
    "additionalProperties": False,
}


def _normalize(text: str) -> str:
    return _WS.sub(" ", text).strip().lower()


def _prose_body(markdown: str) -> str:
    """Article text only: front matter removed, disclaimer block removed."""
    _, body = split_markdown(markdown)
    norm_disc = _normalize(DISCLAIMER)
    # Drop everything from the last '---' separator onward if it is the disclaimer.
    for sep in ("\n---\n", "\n---"):
        idx = body.rfind(sep)
        if idx != -1 and norm_disc in _normalize(body[idx:]):
            body = body[:idx]
            break
    return body.strip()


def deterministic_checks(markdown: str) -> list[str]:
    issues: list[str] = []
    body = _normalize(markdown)
    if _normalize(DISCLAIMER) not in body:
        issues.append("mandatory disclaimer missing or altered")
    for pat in BANNED_PATTERNS:
        m = re.search(pat, body)
        if m:
            issues.append(f"advice/hype phrasing: '{m.group(0)}'")

    prose = _prose_body(markdown)
    words = len(prose.split())
    if words < MIN_BODY_WORDS:
        issues.append(f"body too short ({words} words; min {MIN_BODY_WORDS})")
    elif words > MAX_BODY_WORDS:
        issues.append(f"body too long ({words} words; max {MAX_BODY_WORDS})")
    if _URL_RE.search(prose):
        issues.append("body contains a URL (source link belongs to the template)")
    return issues


def review_article(record: dict, markdown: str) -> dict:
    prompt = (
        "RECORD (JSON):\n```json\n"
        + json.dumps(record, indent=2, ensure_ascii=False)
        + "\n```\n\nARTICLE:\n```markdown\n"
        + markdown
        + "\n```\n"
    )
    return complete_json(REVIEW_SYSTEM, prompt, REVIEW_SCHEMA, max_tokens=1500)


def qa_one(article_entry: dict) -> dict:
    md_path = Path(article_entry["article_path"])
    markdown = md_path.read_text(encoding="utf-8")
    record = article_entry["record"]

    issues = deterministic_checks(markdown)
    try:
        model_result = review_article(record, markdown)
    except Exception as exc:  # noqa: BLE001 - a review failure is a rejection, not a crash
        model_result = {"status": "rejected", "issues": [f"review call failed: {exc}"]}

    issues.extend(model_result.get("issues", []))
    status = "approved" if not issues and model_result.get("status") == "approved" else "rejected"
    return {
        "slug": article_entry["slug"],
        "article_path": str(md_path),
        "status": status,
        "issues": issues,
        "source_url": record.get("source_url"),
    }


def run(date_str: str, output_dir: Path | None = None) -> Path:
    settings.validate_for_llm()
    base = (output_dir or settings.output_dir) / date_str
    manifest_path = base / "articles.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"{manifest_path} not found — run the write agent first.")

    articles = json.loads(manifest_path.read_text(encoding="utf-8"))["articles"]
    results = []
    for i, entry in enumerate(articles, 1):
        res = qa_one(entry)
        results.append(res)
        mark = "OK " if res["status"] == "approved" else "REJ"
        print(f"  [{i}/{len(articles)}] {mark} {res['slug']}"
              + (f" :: {'; '.join(res['issues'])}" if res["issues"] else ""))

    approved = sum(1 for r in results if r["status"] == "approved")
    out_path = base / "qa.json"
    out_path.write_text(
        json.dumps(
            {"date": date_str, "total": len(results), "approved": approved,
             "rejected": len(results) - approved,
             "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
             "results": results},
            indent=2, ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"[qa] {approved}/{len(results)} approved -> {out_path}")
    return out_path


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="QA generated articles against source data.")
    p.add_argument("--date", required=True)
    args = p.parse_args(argv)
    run(args.date)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
