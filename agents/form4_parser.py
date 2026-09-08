"""Deterministic parsers for the SEC EDGAR daily index and Form 4 XML.

No LLM is involved here: Form 4 is a well-structured XML document, so parsing it
in code is more reliable, free, and auditable. Numbers are taken verbatim from
the filing; the only arithmetic performed is summing/averaging the individual
transaction lines within a single filing (never inventing missing values).
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field, asdict
from typing import Any

from .config import TRANSACTION_CODE_MAP

_OWNERSHIP_RE = re.compile(r"<ownershipDocument>.*?</ownershipDocument>", re.DOTALL)
_TRUE = {"1", "true", "yes"}


# --------------------------------------------------------------------------- #
# Daily index                                                                 #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class IndexRow:
    form_type: str
    company_name: str
    cik: str
    date_filed: str
    file_name: str  # e.g. "edgar/data/320193/0000320193-24-000100.txt"


def parse_daily_index(text: str) -> list[IndexRow]:
    """Parse a ``form.<yyyymmdd>.idx`` file into rows.

    The file is fixed-width with a header row naming the columns and a rule of
    dashes beneath it. Column start positions come from the header row.
    """
    lines = text.splitlines()
    header_idx = next(
        (i for i, ln in enumerate(lines) if ln.startswith("Form Type") and "CIK" in ln),
        None,
    )
    if header_idx is None:
        return []

    header = lines[header_idx]
    cols = ["Form Type", "Company Name", "CIK", "Date Filed", "File Name"]
    starts = []
    for name in cols:
        pos = header.find(name)
        if pos == -1:
            return []
        starts.append(pos)
    bounds = list(zip(starts, starts[1:] + [None]))

    rows: list[IndexRow] = []
    for ln in lines[header_idx + 1 :]:
        if not ln.strip() or set(ln.strip()) == {"-"}:
            continue
        parts = [ln[a:b].strip() for a, b in bounds]
        if len(parts) != 5 or not parts[4]:
            continue
        rows.append(
            IndexRow(
                form_type=parts[0],
                company_name=parts[1],
                cik=parts[2],
                date_filed=parts[3],
                file_name=parts[4],
            )
        )
    return rows


def filter_form4_rows(rows: list[IndexRow]) -> list[IndexRow]:
    """Keep Form 4 and Form 4/A rows only."""
    return [r for r in rows if r.form_type.upper() in {"4", "4/A"}]


# --------------------------------------------------------------------------- #
# Form 4 XML                                                                  #
# --------------------------------------------------------------------------- #
@dataclass
class Form4Record:
    filer_name: str | None
    filer_title: str | None
    company_name: str | None
    company_ticker: str | None
    transaction_date: str | None
    transaction_type: str | None  # "purchase" | "sale"
    shares: float | None
    price_per_share: float | None
    total_value: float | None
    source_url: str | None
    # --- internal / provenance (not part of the spec output schema) ---
    issuer_cik: str | None = None
    accession: str | None = None
    is_amendment: bool = False
    transaction_codes: list[str] = field(default_factory=list)
    raw_filing_url: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def extract_ownership_xml(submission_text: str) -> str | None:
    """Pull the ``<ownershipDocument>`` XML out of a full submission .txt file."""
    m = _OWNERSHIP_RE.search(submission_text)
    return m.group(0) if m else None


def _text(node: ET.Element | None, path: str) -> str | None:
    if node is None:
        return None
    el = node.find(path)
    if el is None or el.text is None:
        return None
    return el.text.strip() or None


def _value(node: ET.Element | None, path: str) -> str | None:
    """Read ``<path><value>X</value></path>`` (the footnote-wrapped form)."""
    if node is None:
        return None
    el = node.find(f"{path}/value")
    if el is not None and el.text is not None:
        return el.text.strip() or None
    return _text(node, path)


def _num(raw: str | None) -> float | None:
    if raw is None:
        return None
    try:
        n = float(raw.replace(",", "").strip())
    except ValueError:
        return None
    return n


def _flag(node: ET.Element | None, path: str) -> bool:
    val = _text(node, path)
    return val is not None and val.lower() in _TRUE


def _reporting_owner_title(rel: ET.Element | None) -> str | None:
    if rel is None:
        return None
    parts: list[str] = []
    officer_title = _text(rel, "officerTitle")
    if officer_title:
        parts.append(officer_title)
    elif _flag(rel, "isOfficer"):
        parts.append("Officer")
    if _flag(rel, "isDirector"):
        parts.append("Director")
    if _flag(rel, "isTenPercentOwner"):
        parts.append("10% Owner")
    if _flag(rel, "isOther"):
        other = _text(rel, "otherText")
        parts.append(other or "Other")
    return ", ".join(dict.fromkeys(parts)) or None


def parse_form4(
    xml_text: str,
    *,
    source_url: str | None = None,
    raw_filing_url: str | None = None,
) -> list[Form4Record]:
    """Parse a Form 4 ownership document into one record per transaction direction.

    A filing with both purchases and sales yields two records. Non-derivative
    transactions with codes outside ``TRANSACTION_CODE_MAP`` (grants, gifts, tax
    withholding, option exercises, ...) are ignored for the MVP.
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []

    doc_type = (_text(root, "documentType") or "4").strip()
    is_amendment = doc_type.endswith("/A") or doc_type == "4/A"

    issuer = root.find("issuer")
    company_name = _text(issuer, "issuerName")
    ticker = _text(issuer, "issuerTradingSymbol")
    issuer_cik = _text(issuer, "issuerCik")
    if issuer_cik:
        issuer_cik = issuer_cik.lstrip("0") or "0"

    owner_names: list[str] = []
    titles: list[str] = []
    for owner in root.findall("reportingOwner"):
        name = _value(owner, "reportingOwnerId/rptOwnerName") or _text(
            owner, "reportingOwnerId/rptOwnerName"
        )
        if name:
            owner_names.append(name)
        t = _reporting_owner_title(owner.find("reportingOwnerRelationship"))
        if t:
            titles.append(t)
    filer_name = " / ".join(dict.fromkeys(owner_names)) or None
    filer_title = "; ".join(dict.fromkeys(titles)) or None

    # Collect non-derivative transactions, grouped by resolved direction.
    groups: dict[str, list[dict[str, Any]]] = {"purchase": [], "sale": []}
    for txn in root.findall("nonDerivativeTable/nonDerivativeTransaction"):
        code = (_text(txn, "transactionCoding/transactionCode") or "").strip().upper()
        direction = TRANSACTION_CODE_MAP.get(code)
        if direction is None:
            continue
        shares = _num(_value(txn, "transactionAmounts/transactionShares"))
        price = _num(_value(txn, "transactionAmounts/transactionPricePerShare"))
        date = _value(txn, "transactionDate")
        groups[direction].append(
            {"code": code, "shares": shares, "price": price, "date": date}
        )

    records: list[Form4Record] = []
    for direction, lines in groups.items():
        if not lines:
            continue
        share_vals = [ln["shares"] for ln in lines if ln["shares"] is not None]
        total_shares = sum(share_vals) if share_vals else None

        prices = [ln["price"] for ln in lines if ln["price"] is not None]
        have_all_prices = len(prices) == len(lines) and total_shares
        if have_all_prices:
            total_value = sum(ln["shares"] * ln["price"] for ln in lines)
            distinct = {round(p, 6) for p in prices}
            price_per_share = (
                prices[0]
                if len(distinct) == 1
                else round(total_value / total_shares, 4)
            )
        else:
            total_value = None
            price_per_share = prices[0] if len(prices) == 1 else None

        dates = sorted(ln["date"] for ln in lines if ln["date"])
        records.append(
            Form4Record(
                filer_name=filer_name,
                filer_title=filer_title,
                company_name=company_name,
                company_ticker=ticker,
                transaction_date=dates[-1] if dates else None,
                transaction_type=direction,
                shares=_clean_number(total_shares),
                price_per_share=_clean_number(price_per_share),
                total_value=_clean_number(total_value),
                source_url=source_url,
                issuer_cik=issuer_cik,
                is_amendment=is_amendment,
                transaction_codes=sorted({ln["code"] for ln in lines}),
                raw_filing_url=raw_filing_url,
            )
        )
    return records


def _clean_number(n: float | None) -> float | int | None:
    if n is None:
        return None
    if abs(n - round(n)) < 1e-9:
        return int(round(n))
    return round(n, 4)
