"""Earnings dates from Yahoo (yfinance), cached per ticker. Yahoo's calendar is
imperfect; used only to exclude earnings-affected days."""
import time
from pathlib import Path

import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "earnings"


def earnings_dates(ticker: str) -> pd.DataFrame:
    RAW.mkdir(parents=True, exist_ok=True)
    p = RAW / f"{ticker}.parquet"
    if p.exists():
        return pd.read_parquet(p)
    try:
        d = yf.Ticker(ticker).get_earnings_dates(limit=40)
        d = d.reset_index() if d is not None else pd.DataFrame()
    except Exception as e:  # cache failures as empty so reruns don't hammer Yahoo
        print(ticker, "failed", e)
        d = pd.DataFrame()
    if not d.empty:
        d.columns = [str(c) for c in d.columns]
    d.to_parquet(p)
    time.sleep(1.0)
    return d


if __name__ == "__main__":
    g = pd.read_parquet(ROOT / "data" / "panel" / "stock_gamma.parquet")
    for t in sorted(g["underlying"].unique()):
        d = earnings_dates(t)
        print(t, len(d), flush=True)
