"""N-PORT-P filings made after the latest DERA quarterly data set.

The bulk data sets are keyed by filing quarter and lag by a quarter, so
filings made since the last published set (here: from 2026-07-01) are pulled
filing-by-filing from EDGAR via each trust's submissions JSON and parsed with
flows.nport.parse_nport into the same column layout as the bulk extract.
"""
from __future__ import annotations

import json

import pandas as pd

from common.http import fetch
from common.paths import CACHE
from flows.nport import parse_nport

OUT = CACHE / "nport"
SUBMISSIONS = "https://data.sec.gov/submissions/CIK{cik:010d}.json"


def _trust_nport_filings(cik: int, after: str) -> list[tuple[str, str]]:
    body = fetch(SUBMISSIONS.format(cik=cik), refresh=False)
    js = json.loads(body)
    rec = js["filings"]["recent"]
    out = []
    for form, acc, fdate in zip(rec["form"], rec["accessionNumber"], rec["filingDate"]):
        if form.startswith("NPORT-P") and fdate >= after:
            out.append((acc, fdate))
    return out


def extract_recent(trust_ciks, after: str = "2026-07-01", series_keep: set | None = None) -> None:
    funds, holds = [], []
    for cik in sorted(set(int(c) for c in trust_ciks)):
        for acc, fdate in _trust_nport_filings(cik, after):
            url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc.replace('-', '')}/primary_doc.xml"
            xml = fetch(url, allow_404=True)
            if not xml:
                continue
            try:
                s, h = parse_nport(xml, acc)
            except Exception as e:  # malformed filing
                print("parse fail", acc, e)
                continue
            if series_keep is not None and s["series_id"] not in series_keep:
                continue
            s["filing_date"] = fdate
            s["trust_cik"] = cik
            funds.append(s)
            holds.extend(h)
    f = pd.DataFrame(funds)
    if f.empty:
        return
    f = f.rename(columns={"rep_pd_date": "report_date", "rep_pd_end": "report_ending_period",
                          "is_final": "is_last_filing", "tot_assets": "total_assets",
                          "designated_index": "designated_index_name",
                          "rtn1": "monthly_total_return1", "rtn2": "monthly_total_return2",
                          "rtn3": "monthly_total_return3"})
    for m in (1, 2, 3):
        f = f.rename(columns={f"sales{m}": f"sales_flow_mon{m}", f"redemp{m}": f"redemption_flow_mon{m}",
                              f"reinv{m}": f"reinvestment_flow_mon{m}"})
    for c in ("filing_date", "report_date", "report_ending_period"):
        f[c] = pd.to_datetime(f[c], errors="coerce").dt.strftime("%d-%b-%Y").str.upper()
    f = f.rename(columns={"accession": "accession_number"})
    f["sub_type"] = "NPORT-P"
    f["dataset_quarter"] = "edgar_recent"
    f = f.astype({c: str for c in f.columns})
    h = pd.DataFrame(holds).rename(columns={
        "accession": "accession_number", "name": "issuer_name", "title": "issuer_title", "cusip": "issuer_cusip",
        "val_usd": "currency_value", "pct_val": "percentage", "payoff": "payoff_profile", "units": "unit",
        "isin": "identifier_isin", "ticker": "identifier_ticker", "deriv_cat": "derivative_cat",
        "notional": "notional_amount"})
    h = h.astype({c: str for c in h.columns})
    f.to_parquet(OUT / "funds_edgar_recent.parquet", index=False)
    h.to_parquet(OUT / "holdings_edgar_recent.parquet", index=False)
    print("recent filings", len(f), "holdings", len(h))
