"""60-minute bars (last ~730 days) for LETF underlyings and benchmarks."""
import pandas as pd

from pipelines.fetch_letf_prices import BENCH
from pipelines.prices import download_hourly
from universe.build_universe import ROOT

if __name__ == "__main__":
    v = pd.read_csv(ROOT / "universe" / "letf_universe.csv")
    unds = sorted(set(v.loc[v["lev_check"] != "no_prices", "underlying"].dropna()))
    t = unds + [b for b in BENCH if not b.startswith("^")]
    print(len(t), "tickers")
    download_hourly(t)
