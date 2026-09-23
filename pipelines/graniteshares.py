"""GraniteShares daily NAV + AUM history via the public API their fund pages use."""
import json
import re
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "issuer" / "graniteshares"
NAV_URL = (
    "https://knockoutv2.azurewebsites.net/api/ProductNavHistory/triggers/When_a_HTTP_request_is_received/invoke/{pid}"
    "?api-version=2022-05-01&sp=%2Ftriggers%2FWhen_a_HTTP_request_is_received%2Frun&sv=1.0"
    "&sig=bH7VS-AEVsHFaoHEdwodgWM-T_MUr8kOaZi9St7whis"
)
HDR = {"User-Agent": "Mozilla/5.0 (research; joshswartz@gmail.com)"}


def product_id(ticker: str):
    p = RAW / "product_ids.json"
    ids = json.loads(p.read_text()) if p.exists() else {}
    if ticker in ids:
        return ids[ticker]
    r = requests.get(f"https://graniteshares.com/etfs/{ticker.lower()}/", headers=HDR, timeout=60)
    m = re.search(r"PRODUCT_ID\s*=\s*(\d+)", r.text) if r.status_code == 200 else None
    ids[ticker] = int(m.group(1)) if m else None
    p.write_text(json.dumps(ids, indent=1))
    time.sleep(0.5)
    return ids[ticker]


def nav_history(ticker: str) -> pd.DataFrame:
    p = RAW / f"navhistory_{ticker}.json"
    if not p.exists():
        pid = product_id(ticker)
        if pid is None:
            return pd.DataFrame()
        r = requests.get(NAV_URL.format(pid=pid), headers=HDR, timeout=60)
        r.raise_for_status()
        p.write_text(r.text)
        time.sleep(0.5)
    d = pd.DataFrame(json.loads(p.read_text()))
    if d.empty:
        return d
    d = d[d["IsDeleted"] == 0]
    d = d.assign(date=pd.to_datetime(d["PriceDate"]), nav=d["Price"], aum=d["AUM"])
    d = d.sort_values(["date", "PriceHistoryId"]).drop_duplicates("date", keep="last")
    return d[["date", "nav", "aum"]].assign(ticker=ticker).reset_index(drop=True)


if __name__ == "__main__":
    u = pd.read_csv(ROOT / "universe" / "letf_universe_raw.csv")
    gs = u[u["trust"].str.contains("GraniteShares", na=False) & u["has_ticker"]]
    out = []
    for t in sorted(gs["ticker"].unique()):
        d = nav_history(t)
        print(t, len(d), flush=True)
        out.append(d)
    pd.concat(out).to_parquet(RAW / "graniteshares_nav_aum.parquet")
