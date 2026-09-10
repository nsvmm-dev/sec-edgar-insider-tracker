"""Helpers for article files: slugs and (minimal) YAML front matter.

We keep a tiny hand-rolled front-matter reader/writer so the pipeline has no
YAML dependency. Values are limited to strings, numbers, booleans and null —
which is all the article metadata needs.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any

_SLUG_RE = re.compile(r"[^a-z0-9]+")

_ACTOR_RE = re.compile(
    r"^(.*?)(?:\s+\([^)]*\))?\s+(?:Buys?|Sells?|Bought|Sold|Purchases?|Acquires?)\b",
    re.IGNORECASE,
)

_KEEP_UPPER = {
    "NVIDIA", "IBM", "AMD", "HP", "UPS", "PNC", "MSCI", "ADP", "CDW", "DXC",
    "AON", "EOG", "PPG", "MMM", "AES", "APA", "CME", "ICE", "FMC", "BXP",
    "WEC", "DTE", "AEP", "CMS", "NRG", "EQT", "HES", "LKQ", "GEHC", "USA",
    "US", "AI", "TV", "IT", "KKR",
}
_WORD_MAP = {
    "CORP": "Corp", "CORP.": "Corp.", "CORPORATION": "Corporation",
    "INC": "Inc", "INC.": "Inc.", "CO": "Co", "CO.": "Co.",
    "LTD": "Ltd", "LTD.": "Ltd.", "PLC": "plc", "LLC": "LLC", "LP": "LP",
    "HOLDINGS": "Holdings", "HOLDING": "Holding", "GROUP": "Group",
    "COMPANIES": "Companies", "COMPANY": "Company",
    "INTERNATIONAL": "International", "TECHNOLOGIES": "Technologies",
    "TECHNOLOGY": "Technology", "SYSTEMS": "Systems",
    "THE": "the", "AND": "and", "OF": "of",
}


def slugify(*parts: str) -> str:
    joined = "-".join(str(p) for p in parts if p)
    return _SLUG_RE.sub("-", joined.lower()).strip("-")


def actor_from_headline(title: str | None, fallback: str | None = None) -> str | None:
    """Pull the person/entity name out of a "<Name> (<role>) Sells ..." headline.

    Falls back to ``fallback`` (usually the raw EDGAR ``filer`` field) when the
    headline does not match the expected pattern.
    """
    m = _ACTOR_RE.match(title or "")
    name = m.group(1).strip() if m else ""
    return name or fallback


def title_case_company(name: str | None) -> str | None:
    """ALL-CAPS EDGAR issuer name -> title case ("STARBUCKS CORP" -> "Starbucks Corp").

    Names that already contain lower-case letters are returned unchanged.
    """
    if not name or name != name.upper():
        return name
    words = name.split()
    out = []
    for i, w in enumerate(words):
        if w in _KEEP_UPPER:
            out.append(w)
        elif w in _WORD_MAP:
            mapped = _WORD_MAP[w]
            out.append(mapped[:1].upper() + mapped[1:] if i == 0 else mapped)
        elif w.isdigit() or re.fullmatch(r"[A-Z]&[A-Z]", w):
            out.append(w)
        else:
            out.append(w[:1].upper() + w[1:].lower())
    return " ".join(out)


def article_slug(record: dict[str, Any]) -> str:
    digest = hashlib.sha1(
        (record.get("source_url") or "").encode("utf-8")
    ).hexdigest()[:8]
    return slugify(
        record.get("transaction_date") or "undated",
        record.get("company_ticker") or "unknown",
        record.get("transaction_type") or "trade",
        digest,
    )


def _fmt_value(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return repr(value)
    text = str(value).replace('"', '\\"')
    return f'"{text}"'


def _parse_value(raw: str) -> Any:
    raw = raw.strip()
    if raw in ("null", "~", ""):
        return None
    if raw in ("true", "false"):
        return raw == "true"
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "\"'":
        return raw[1:-1].replace('\\"', '"')
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        return raw


def build_markdown(front_matter: dict[str, Any], body: str) -> str:
    lines = ["---"]
    for key, value in front_matter.items():
        lines.append(f"{key}: {_fmt_value(value)}")
    lines.append("---")
    return "\n".join(lines) + "\n\n" + body.strip() + "\n"


def split_markdown(text: str) -> tuple[dict[str, Any], str]:
    """Return (front_matter_dict, body). Tolerates a missing front-matter block."""
    if not text.startswith("---"):
        return {}, text.strip()
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text.strip()
    fm: dict[str, Any] = {}
    for line in parts[1].strip().splitlines():
        if not line.strip() or line.lstrip().startswith("#") or ":" not in line:
            continue
        key, _, raw = line.partition(":")
        fm[key.strip()] = _parse_value(raw)
    return fm, parts[2].strip()
