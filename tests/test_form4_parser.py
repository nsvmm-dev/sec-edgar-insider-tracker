"""Parser tests. Run with `python -m pytest` or `python tests/test_form4_parser.py`."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.form4_parser import (  # noqa: E402
    extract_ownership_xml,
    filter_form4_rows,
    parse_daily_index,
    parse_form4,
)

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "form4_sample.xml"

SAMPLE_IDX = """\
Description:           Daily Index of EDGAR Dissemination Feed
Last Data Received:    September 04, 2026

Form Type   Company Name                                                  CIK         Date Filed  File Name
---------------------------------------------------------------------------------------------------------------------------------------------
4           DOE JANE Q                                                    1214128     2026-09-04  edgar/data/1214128/0001214128-26-000045.txt
4/A         SMITH JOHN                                                    1500000     2026-09-04  edgar/data/1500000/0001500000-26-000012.txt
8-K         SOME COMPANY INC                                              111111      2026-09-04  edgar/data/111111/0000111111-26-000099.txt
"""


def test_daily_index_parses_columns():
    rows = parse_daily_index(SAMPLE_IDX)
    assert len(rows) == 3
    assert rows[0].form_type == "4"
    assert rows[0].company_name == "DOE JANE Q"
    assert rows[0].cik == "1214128"
    assert rows[0].file_name == "edgar/data/1214128/0001214128-26-000045.txt"
    form4 = filter_form4_rows(rows)
    assert {r.form_type for r in form4} == {"4", "4/A"}
    assert len(form4) == 2


def test_extract_ownership_xml_from_sgml():
    blob = (
        "<SEC-DOCUMENT>\n<DOCUMENT>\n<TYPE>4\n<XML>\n"
        "<ownershipDocument><documentType>4</documentType>"
        "<issuer><issuerName>X</issuerName></issuer></ownershipDocument>\n"
        "</XML>\n</DOCUMENT>\n</SEC-DOCUMENT>"
    )
    xml = extract_ownership_xml(blob)
    assert xml is not None and xml.startswith("<ownershipDocument>")


def test_parse_form4_groups_by_direction():
    records = parse_form4(
        FIXTURE.read_text(encoding="utf-8"),
        source_url="https://example.test/index.htm",
    )
    by_type = {r.transaction_type: r for r in records}
    assert set(by_type) == {"sale", "purchase"}

    sale = by_type["sale"]
    assert sale.filer_name == "DOE JANE Q"
    assert sale.filer_title == "Senior Vice President, CFO"
    assert sale.company_name == "Apple Inc."
    assert sale.company_ticker == "AAPL"
    assert sale.issuer_cik == "320193"
    assert sale.shares == 15000
    assert sale.price_per_share == 231  # weighted average of 230.50 / 232.00
    assert sale.total_value == 3_465_000
    assert sale.transaction_date == "2026-09-04"
    assert sale.transaction_codes == ["S"]
    assert sale.source_url == "https://example.test/index.htm"

    purchase = by_type["purchase"]
    assert purchase.shares == 1200
    assert purchase.price_per_share == 231
    assert purchase.total_value == 277_200
    # The 'A' (award) line must be ignored entirely.
    assert purchase.transaction_codes == ["P"]


def test_parse_form4_handles_garbage():
    assert parse_form4("<not-xml", source_url="x") == []


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except AssertionError as exc:
            failed += 1
            print(f"FAIL {fn.__name__}: {exc}")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"ERROR {fn.__name__}: {exc!r}")
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(_run_all())
