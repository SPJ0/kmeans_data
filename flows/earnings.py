"""Earnings-announcement dates from free sources.

Primary: SEC 8-K filings carrying Item 2.02 (Results of Operations), from each
company's data.sec.gov submissions JSON. Fallback / union: yfinance earnings
dates (unreliable, but covers foreign filers that report on 6-K).

EDGAR assigns filings accepted after 17:30 ET the next business day's date,
so the exclusion window is generous: trade dates D-2 .. D+1 around the 8-K
date D, and D-1 .. D+1 around a yfinance date.
"""
from __future__ import annotations

import json

import pandas as pd

from common.http import fetch
from common.paths import CACHE, RAW

OUT = CACHE / "earnings_dates.parquet"


def _cik_map() -> dict:
    ex = json.load(open(RAW / "sec" / "company_tickers_exchange.json"))
    return {r[2].replace(".", "-"): int(r[0]) for r in ex["data"]}


def sec_8k_202(cik: int) -> list[str]:
    js = json.loads(fetch(f"https://data.sec.gov/submissions/CIK{cik:010d}.json"))
    blocks = [js["filings"]["recent"]]
    for f in js["filings"].get("files", []):
        if f.get("filingTo", "9999") >= "2021-06-01":
            blocks.append(json.loads(fetch("https://data.sec.gov/submissions/" + f["name"])))
    dates = []
    for b in blocks:
        for form, items, d in zip(b["form"], b.get("items", [""] * len(b["form"])), b["filingDate"]):
            if form in ("8-K", "8-K/A") and "2.02" in str(items) and d >= "2021-06-01":
                dates.append(d)
    return sorted(set(dates))


def yf_dates(ticker: str) -> list[str]:
    import yfinance as yf
    try:
        df = yf.Ticker(ticker).get_earnings_dates(limit=40)
    except Exception:
        return []
    if df is None or df.empty:
        return []
    idx = pd.to_datetime(df.index)
    if idx.tz is not None:
        # after-close releases stamped in US/Eastern keep their calendar date
        idx = idx.tz_convert("America/New_York").tz_localize(None)
    return sorted({d.strftime("%Y-%m-%d") for d in idx if d >= pd.Timestamp("2021-06-01")})


def build(tickers, use_yf: bool = True) -> pd.DataFrame:
    have = pd.read_parquet(OUT) if OUT.exists() else pd.DataFrame(columns=["ticker", "date", "source"])
    done = set(have["ticker"])
    cik = _cik_map()
    rows = []
    for i, t in enumerate(t for t in dict.fromkeys(tickers) if t not in done):
        got = False
        if t in cik:
            try:
                for d in sec_8k_202(cik[t]):
                    rows.append((t, d, "sec_8k_2.02"))
                    got = True
            except Exception as e:
                print("sec fail", t, e)
        if use_yf and not got:
            for d in yf_dates(t):
                rows.append((t, d, "yfinance"))
                got = True
        if not got:
            rows.append((t, None, "none"))
        if i % 100 == 0:
            print("earnings", i, flush=True)
    new = pd.DataFrame(rows, columns=["ticker", "date", "source"])
    out = pd.concat([have, new], ignore_index=True)
    out.to_parquet(OUT, index=False)
    return out


def exclusion_mask(panel: pd.DataFrame, ed: pd.DataFrame) -> pd.Series:
    """True for stock-days whose trade date is within the earnings window."""
    ed = ed.dropna(subset=["date"])
    excl = set()
    cal = pd.DatetimeIndex(sorted(panel["date"].unique()))
    for t, d, src in ed[["ticker", "date", "source"]].itertuples(index=False):
        pos = cal.searchsorted(pd.Timestamp(d))
        lo, hi = (-2, 1) if src.startswith("sec") else (-1, 1)
        for k in range(lo, hi + 1):
            if 0 <= pos + k < len(cal):
                excl.add((t, cal[pos + k]))
    keys = list(zip(panel["ticker"], panel["date"]))
    return pd.Series([k in excl for k in keys], index=panel.index)
