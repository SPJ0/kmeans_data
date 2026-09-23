"""Download the SEC reference files the universe build reads (cached; rerun is a no-op).

  * Investment Company Series & Class files, 2022-2026 (all registered series, incl. closed)
  * company_tickers_exchange.json (operating-company tickers), company_tickers_mf.json (fund tickers)
  * S&P 1500 constituent lists from Wikipedia (placebo pool; current constituents -> survivorship caveat)
"""
from __future__ import annotations

import io

import pandas as pd

from common.http import fetch
from common.paths import RAW

SC = {
    2026: "https://www.sec.gov/files/investment/data/other/investment-company-series-class-information/investment-company-series-class-2026.csv",
    2025: "https://www.sec.gov/files/investment/data/other/investment-company-series-class-information/investment-company-series-class-2025.csv",
    2024: "https://www.sec.gov/files/investment/data/other/investment-company-series-and-class-information/investment-company-series-class-2024.csv",
    2023: "https://www.sec.gov/files/investment/data/other/investment-company-series-class-information/investment_company_series_class_2023.csv",
    2022: "https://www.sec.gov/files/investment/data/other/investment-company-series-and-class-information/investment_company_series_class_2022.csv",
}
WIKI = {"sp500": "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
        "sp400": "https://en.wikipedia.org/wiki/List_of_S%26P_400_companies",
        "sp600": "https://en.wikipedia.org/wiki/List_of_S%26P_600_companies"}


def main(asof: str = "2026-09-23") -> None:
    (RAW / "sec").mkdir(parents=True, exist_ok=True)
    for y, url in SC.items():
        p = RAW / "sec" / f"series_class_{y}.csv"
        if not p.exists():
            p.write_bytes(fetch(url))
    for name in ("company_tickers_exchange.json", "company_tickers_mf.json"):
        p = RAW / "sec" / name
        if not p.exists():
            p.write_bytes(fetch(f"https://www.sec.gov/files/{name}"))
    out = RAW / "lists" / f"placebo_pool_{asof}.csv"
    if not out.exists():
        out.parent.mkdir(parents=True, exist_ok=True)
        rows = []
        for k, url in WIKI.items():
            for t in pd.read_html(io.StringIO(fetch(url).decode("utf-8", "replace"))):
                col = [c for c in t.columns if str(c).lower() in ("symbol", "ticker", "ticker symbol")]
                if col and len(t) > 50:
                    rows += [(k, str(x).replace(".", "-")) for x in t[col[0]]]
                    break
        pd.DataFrame(rows, columns=["list", "ticker"]).drop_duplicates().to_csv(out, index=False)


if __name__ == "__main__":
    main()
