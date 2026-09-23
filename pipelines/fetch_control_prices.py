"""Daily prices for all currently listed US common stocks (control universe).

Survivorship note: current listings only. Fine for estimating the generic
reversal relation among liquid names; not used as the treated sample.
"""
import pandas as pd

from pipelines.prices import download_daily
from universe.build_universe import ROOT

JUNK = r"warrant|\bunits?\b|\bright|preferred|notes? due|debentures|%|depositary shares, each representing a fraction|trust preferred|acquisition corp"


def control_tickers() -> list[str]:
    d = ROOT / "data" / "raw" / "nasdaqtrader"
    n = pd.read_csv(d / "nasdaqlisted_2026-09-23.txt", sep="|", dtype=str, keep_default_na=False).iloc[:-1]
    o = pd.read_csv(d / "otherlisted_2026-09-23.txt", sep="|", dtype=str, keep_default_na=False).iloc[:-1]
    n = n[(n["ETF"] == "N") & (n["Test Issue"] == "N")][["Symbol", "Security Name"]]
    o = o[(o["ETF"] == "N") & (o["Test Issue"] == "N")].rename(columns={"ACT Symbol": "Symbol"})[["Symbol", "Security Name"]]
    a = pd.concat([n, o])
    a = a[~a["Security Name"].str.contains(JUNK, case=False, na=False, regex=True)]
    a = a[~a["Symbol"].str.contains(r"[\$\.]", regex=True)]
    return sorted(a["Symbol"].str.strip().unique())


if __name__ == "__main__":
    t = control_tickers()
    print(len(t), "control tickers")
    download_daily(t, batch=100, pause=2.0)
