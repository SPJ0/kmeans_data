"""SEC Form N-PORT: quarter-end net assets, monthly flows/returns and exposure.

Stages (each cached):
  1. EDGAR full-text search per series -> list of NPORT-P filings
  2. fetch each filing's primary_doc.xml (gzipped on disk)
  3. parse -> data/nport/nport_fund.parquet (one row per filing)
             data/nport/nport_exposure.parquet (one row per filing x reference ticker)

Only fiscal-quarter-end reports are public, but each carries flows and returns
for all three months of the quarter, so month-end assets can be rebuilt.
"""

from __future__ import annotations

import gzip
import json
import re
import sys
import threading
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "nport"
OUT = ROOT / "data" / "nport"
UA = {"User-Agent": "research joshswartz@gmail.com"}
PAUSE = 0.0  # pacing is done by the global limiter below
MIN_PERIOD = "2021-06-30"
# Major index LETFs kept as a sanity check on the mechanism.
INDEX_LETFS = {
    "TQQQ", "SQQQ", "QLD", "QID", "SOXL", "SOXS", "UPRO", "SPXU", "SPXL", "SPXS", "SSO", "SDS",
    "TNA", "TZA", "UDOW", "SDOW", "TECL", "TECS", "FAS", "FAZ", "LABU", "LABD", "USD", "SSG",
    "BITX", "BITU", "SBIT", "ETHU", "NUGT", "DUST", "GUSH", "DRIP", "YINN", "YANG", "TMF", "TMV",
}
_lock = threading.Lock()
_last = [0.0]


def _throttle(rate: float = 8.0) -> None:
    with _lock:
        wait = _last[0] + 1.0 / rate - time.time()
        if wait > 0:
            time.sleep(wait)
        _last[0] = time.time()


def _get(url: str, tries: int = 5) -> requests.Response:
    for k in range(tries):
        _throttle()
        r = requests.get(url, headers=UA, timeout=60)
        if r.status_code == 200:
            return r
        time.sleep(2 ** (k + 1))
    r.raise_for_status()
    return r


def search_filings(series_id: str, refresh: bool = False) -> list[dict]:
    p = RAW / "search" / f"{series_id}.json"
    if p.exists() and not refresh:
        return json.loads(p.read_text())
    p.parent.mkdir(parents=True, exist_ok=True)
    hits, start = [], 0
    while True:
        url = f'https://efts.sec.gov/LATEST/search-index?q=%22{series_id}%22&forms=NPORT-P&from={start}'
        d = _get(url).json()
        batch = d["hits"]["hits"]
        for h in batch:
            s = h["_source"]
            hits.append(
                dict(accession=h["_id"].split(":")[0], cik=s["ciks"][0], period=s.get("period_ending"),
                     file_date=s.get("file_date"), form=s.get("form"))
            )
        start += len(batch)
        time.sleep(PAUSE)
        if not batch or start >= d["hits"]["total"]["value"]:
            break
    p.write_text(json.dumps(hits))
    return hits


def fetch_xml(cik: str, accession: str) -> bytes:
    p = RAW / "xml" / f"{accession}.xml.gz"
    if p.exists():
        return gzip.decompress(p.read_bytes())
    p.parent.mkdir(parents=True, exist_ok=True)
    url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace('-', '')}/primary_doc.xml"
    b = _get(url).content
    p.write_bytes(gzip.compress(b))
    time.sleep(PAUSE)
    return b


def _strip_ns(root: ET.Element) -> ET.Element:
    for el in root.iter():
        if "}" in el.tag:
            el.tag = el.tag.split("}", 1)[1]
    return root


def _f(x) -> float | None:
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def parse_filing(xml: bytes) -> tuple[dict, list[dict]]:
    root = _strip_ns(ET.fromstring(xml))
    gen = root.find(".//genInfo")
    fund = root.find(".//fundInfo")
    info = dict(
        series_id=(gen.findtext("seriesId") if gen is not None else None),
        rep_date=(gen.findtext("repPdDate") if gen is not None else None),
        fy_end=(gen.findtext("repPdEnd") if gen is not None else None),
        tot_assets=_f(fund.findtext("totAssets")) if fund is not None else None,
        net_assets=_f(fund.findtext("netAssets")) if fund is not None else None,
    )
    rets = root.findall(".//monthlyTotReturn")
    if rets:
        for k in (1, 2, 3):
            info[f"ret{k}"] = _f(rets[0].get(f"rtn{k}"))
        info["n_classes"] = len(rets)
    for k in (1, 2, 3):
        fl = root.find(f".//mon{k}Flow")
        if fl is not None:
            info[f"sales{k}"] = _f(fl.get("sales"))
            info[f"redemption{k}"] = _f(fl.get("redemption"))
            info[f"reinvest{k}"] = _f(fl.get("reinvestment"))

    rows = []
    for sec in root.iter("invstOrSec"):
        cat = sec.findtext("assetCat")
        val = _f(sec.findtext("valUSD")) or 0.0
        payoff = sec.findtext("payoffProfile")
        tick = sec.find(".//identifiers/ticker")
        ticker = tick.get("value") if tick is not None else None
        title = sec.findtext("title") or ""
        swap = sec.find(".//swapDeriv")
        opt = sec.find(".//optionSwaptionWarrantDeriv")
        fut = sec.find(".//futrDeriv")
        if swap is not None:
            ref = swap.findtext(".//descRefInstrmnt//indexIdentifier") or swap.findtext(
                ".//descRefInstrmnt//ticker"
            )
            if ref is None:
                t = swap.find(".//descRefInstrmnt//ticker")
                ref = t.get("value") if t is not None else None
            notional = _f(swap.findtext("notionalAmt")) or 0.0
            unreal = _f(swap.findtext("unrealizedAppr")) or 0.0
            rec = swap.find("floatingRecDesc")
            pay = swap.find("floatingPmntDesc")
            rec_idx = (rec.get("floatingRtIndex") if rec is not None else "") or ""
            pay_idx = (pay.get("floatingRtIndex") if pay is not None else "") or ""
            # The total-return leg is the one that is not a rate (SOFR/OBFR/Fed Funds/etc).
            rate = re.compile(r"sofr|obfr|fed ?fund|libor|effr|overnight|rate|%", re.I)
            if rec_idx and not rate.search(rec_idx):
                sign = 1.0
            elif pay_idx and not rate.search(pay_idx):
                sign = -1.0
            else:
                sign = float("nan")
            rows.append(dict(kind="swap", ref=ref, title=title, notional=notional, unrealized=unreal,
                             sign=sign, value=val, rec_leg=rec_idx[:80], pay_leg=pay_idx[:80]))
        elif opt is not None:
            t = opt.find(".//descRefInstrmnt//ticker")
            ref = t.get("value") if t is not None else opt.findtext(".//descRefInstrmnt//indexIdentifier")
            rows.append(dict(kind="option", ref=ref, title=title, value=val,
                             put_call=opt.findtext("putOrCall"), written=opt.findtext("writtenOrPur"),
                             shares=_f(opt.findtext("shareNo")), strike=_f(opt.findtext("exercisePrice")),
                             expiry=opt.findtext("expDt"), delta=_f(opt.findtext("delta"))))
        elif fut is not None:
            rows.append(dict(kind="future", ref=fut.findtext(".//descRefInstrmnt//indexIdentifier"),
                             title=title, notional=_f(fut.findtext("notionalAmt")), value=val,
                             sign=1.0 if fut.findtext("payOffProf") == "Long" else -1.0))
        elif cat in ("EC", "EP") or ticker:
            rows.append(dict(kind="stock", ref=ticker, title=title, value=val,
                             sign=-1.0 if payoff == "Short" else 1.0,
                             shares=_f(sec.findtext("balance"))))
    for r in rows:
        r["series_id"] = info["series_id"]
        r["rep_date"] = info["rep_date"]
    return info, rows


def _one_series(sid: str) -> tuple[list[dict], list[dict]]:
    funds, holds = [], []
    try:
        filings = search_filings(sid)
    except Exception as e:  # keep going; a rerun retries uncached work
        print("search failed", sid, e, file=sys.stderr)
        return funds, holds
    for f in filings:
        if (f["period"] or "") < MIN_PERIOD:
            continue
        try:
            info, rows = parse_filing(fetch_xml(f["cik"], f["accession"]))
        except Exception as e:
            print("filing failed", sid, f["accession"], e, file=sys.stderr)
            continue
        info.update(accession=f["accession"], file_date=f["file_date"], query_series=sid)
        funds.append(info)
        holds.extend(rows)
    return funds, holds


def run(series_ids: list[str], workers: int = 8) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    funds, holds = [], []
    with ThreadPoolExecutor(workers) as ex:
        for i, (fd_, hd_) in enumerate(ex.map(_one_series, series_ids)):
            funds.extend(fd_)
            holds.extend(hd_)
            if i % 25 == 0:
                print(f"{i}/{len(series_ids)} series, {len(funds)} filings", flush=True)
    fd = pd.DataFrame(funds)
    # Full-text search can match a filing that merely mentions the series id.
    fd = fd[fd["series_id"] == fd["query_series"]].drop_duplicates("accession")
    fd.to_parquet(OUT / "nport_fund.parquet")
    hd = pd.DataFrame(holds)
    hd = hd[hd["series_id"].isin(set(fd["series_id"]))]
    hd.to_parquet(OUT / "nport_holdings.parquet")
    print(f"done: {len(fd)} filings, {len(hd)} holdings rows")


if __name__ == "__main__":
    u = pd.read_csv(ROOT / "universe" / "letf_universe_raw.csv")
    tick = u["all_tickers"].fillna("").str.split(r"\s*\|\s*")
    is_index = tick.apply(lambda ts: bool(set(ts) & INDEX_LETFS)) & (u["category"] == "index_other")
    sel = u[u["has_ticker"] & ((u["category"] == "single_stock") | is_index)]
    run(sorted(sel["series_id"].unique()))
