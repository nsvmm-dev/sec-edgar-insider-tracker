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


def slugify(*parts: str) -> str:
    joined = "-".join(str(p) for p in parts if p)
    return _SLUG_RE.sub("-", joined.lower()).strip("-")


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
