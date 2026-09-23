"""Fetch daily prices for every LETF ticker in the raw universe, their underlyings and benchmarks."""
import pandas as pd

from pipelines.prices import download_daily
from universe.build_universe import ROOT

BENCH = ["SPY", "QQQ", "SMH", "IWM", "IBIT", "BITO", "ARKK", "XLK", "XLF", "XLE", "XBI", "^VIX"]

if __name__ == "__main__":
    u = pd.read_csv(ROOT / "universe" / "letf_universe_raw.csv")
    fund_tickers = set()
    for s in u["all_tickers"].dropna():
        fund_tickers.update(t.strip() for t in s.split("|"))
    unds = set(u.loc[u.category == "single_stock", "underlying"].dropna())
    tickers = sorted(unds | set(BENCH)) + sorted(fund_tickers - unds)
    print(len(tickers), "tickers")
    download_daily(tickers)
