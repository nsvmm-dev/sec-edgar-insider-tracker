"""Central configuration + shared constants for the agent pipeline.

All runtime knobs come from environment variables (see .env.example). Import
`settings` for values and the module-level constants for fixed text such as the
mandatory disclaimer.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:  # optional; the pipeline also works with real env vars only
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover - dotenv is a convenience, not a requirement
    pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# SEC EDGAR hosts. The JSON APIs live on data.sec.gov; the filing Archives
# (daily-index, full submission text, Form 4 XML) live on www.sec.gov.
SEC_ARCHIVES_BASE = "https://www.sec.gov"
SEC_DATA_BASE = "https://data.sec.gov"

# Mandatory disclaimer — spec section 3. This exact wording (whitespace-normalised)
# must appear at the end of every published article; the QA agent enforces it.
DISCLAIMER = (
    "This article is for informational purposes only and does not constitute "
    "investment advice. Insider transactions do not necessarily indicate future "
    "stock performance. Data is sourced from SEC EDGAR and may be subject to "
    "delay or amendment. Always conduct your own research or consult a "
    "licensed financial advisor before making investment decisions."
)

# Form 4 non-derivative transaction codes we treat as newsworthy open-market
# activity. Everything else (grants, gifts, tax withholding, option exercises,
# ...) is ignored for the MVP.
TRANSACTION_CODE_MAP = {
    "P": "purchase",
    "S": "sale",
}


def _clean(value: str | None) -> str:
    return (value or "").strip().strip('"').strip("'")


def _resolve_path(raw: str, default: str) -> Path:
    p = Path(_clean(raw) or default)
    return p if p.is_absolute() else (PROJECT_ROOT / p)


@dataclass(frozen=True)
class Settings:
    anthropic_model: str
    sec_user_agent: str
    sec_request_delay_sec: float
    min_total_value_usd: float
    output_dir: Path
    site_content_dir: Path
    sp500_ciks_path: Path
    published_index_path: Path

    def validate_for_fetch(self) -> None:
        ua = self.sec_user_agent
        if not ua or "yoursite.com" in ua or "@" not in ua:
            raise RuntimeError(
                "SEC_USER_AGENT must be set to '<app name> <your real contact email>'. "
                "SEC rejects requests with a missing or placeholder User-Agent (HTTP 403)."
            )

    def validate_for_llm(self) -> None:
        if not os.environ.get("ANTHROPIC_API_KEY") and not os.environ.get(
            "ANTHROPIC_AUTH_TOKEN"
        ):
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set — the write/QA agents need it."
            )


def load_settings() -> Settings:
    return Settings(
        anthropic_model=_clean(os.environ.get("ANTHROPIC_MODEL")) or "claude-opus-5",
        sec_user_agent=_clean(os.environ.get("SEC_USER_AGENT")),
        sec_request_delay_sec=float(_clean(os.environ.get("SEC_REQUEST_DELAY_SEC")) or "0.15"),
        min_total_value_usd=float(_clean(os.environ.get("MIN_TOTAL_VALUE_USD")) or "0"),
        output_dir=_resolve_path(os.environ.get("OUTPUT_DIR", ""), "./output"),
        site_content_dir=_resolve_path(
            os.environ.get("SITE_CONTENT_DIR", ""), "./site/src/content/articles"
        ),
        sp500_ciks_path=_resolve_path(
            os.environ.get("SP500_CIKS_PATH", ""), "./data/sp500_ciks.json"
        ),
        published_index_path=_resolve_path(
            os.environ.get("PUBLISHED_INDEX_PATH", ""), "./data/published_index.json"
        ),
    )


settings = load_settings()
