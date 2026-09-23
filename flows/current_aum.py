"""Latest fund AUM (anchor + validation target).

Yahoo's quoteSummary endpoint (``Ticker.info``) returns HTTP 401 from this
environment, so the latest AUM, shares outstanding and inception date come
from stockanalysis.com ETF pages, which republish issuer data. The as-of date
is not exact (pages refresh daily; fetched 2026-09-23), so this anchor is
treated as the 2026-09-22 close with a few days' uncertainty.
Raw pages are cached by common.http; parsed rows go to data/cache/current_aum.parquet.
"""
from __future__ import annotations

import re

import pandas as pd

from common.http import MIN_INTERVAL, fetch
from common.paths import CACHE

OUT = CACHE / "current_aum.parquet"
URL = "https://stockanalysis.com/etf/{t}/"
MIN_INTERVAL["stockanalysis.com"] = 1.0

_MULT = {"K": 1e3, "M": 1e6, "B": 1e9, "T": 1e12}


def _num(s: str | None) -> float | None:
    if not s:
        return None
    m = re.match(r"\$?([0-9.,]+)\s*([KMBT])?", s)
    if not m:
        return None
    return float(m.group(1).replace(",", "")) * _MULT.get(m.group(2) or "", 1.0)


def parse_page(html: str) -> dict:
    g = lambda pat: (re.search(pat, html).group(1) if re.search(pat, html) else None)  # noqa: E731
    return {"total_assets": _num(g(r'aum:"([^"]+)"')), "shares_out": _num(g(r'sharesOut:"([^"]+)"')),
            "inception": g(r'inception:"(\d{4}-\d{2}-\d{2})"'), "aum_raw": g(r'aum:"([^"]+)"')}


def fetch_current(tickers) -> pd.DataFrame:
    rows = []
    for i, t in enumerate(dict.fromkeys(tickers)):
        try:
            body = fetch(URL.format(t=t.lower()), allow_404=True)
        except Exception as e:  # blocked / network
            print("aum fail", t, e)
            body = None
        row = {"ticker": t, "source": "stockanalysis.com", "asof": pd.Timestamp("2026-09-22")}
        row.update(parse_page(body.decode("utf-8", "replace")) if body else {})
        rows.append(row)
        if i % 50 == 0:
            print("aum", i, flush=True)
    out = pd.DataFrame(rows)
    out.to_parquet(OUT, index=False)
    return out
