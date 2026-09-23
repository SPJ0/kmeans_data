"""Parse N-PORT-P primary_doc.xml into a fund summary row and holdings rows.

Public N-PORT gives, per fiscal-quarter-end report date: net assets, the three
monthly total returns and monthly creations/redemptions, the designated
reference index (for single-stock funds e.g. "MSTR US EQUITY") and holdings
including swap notionals.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET

import pandas as pd

from common.http import fetch
from universe.edgar import primary_doc_url

NS = {"n": "http://www.sec.gov/edgar/nport", "com": "http://www.sec.gov/edgar/common",
      "ncom": "http://www.sec.gov/edgar/nportcommon"}


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _text(el, path):
    x = el.find(path, NS)
    return x.text.strip() if x is not None and x.text else None


def parse_nport(xml: bytes, accession: str) -> tuple[dict, list[dict]]:
    root = ET.fromstring(xml)
    gi = root.find(".//n:formData/n:genInfo", NS)
    fi = root.find(".//n:formData/n:fundInfo", NS)
    s = {
        "accession": accession,
        "series_id": _text(gi, "n:seriesId"),
        "series_name": _text(gi, "n:seriesName"),
        "rep_pd_date": _text(gi, "n:repPdDate"),
        "rep_pd_end": _text(gi, "n:repPdEnd"),
        "is_final": _text(gi, "n:isFinalFiling"),
        "tot_assets": _f(_text(fi, "n:totAssets")),
        "net_assets": _f(_text(fi, "n:netAssets")),
        "designated_index": _text(fi, ".//n:fundsDesignatedInfo/n:nameDesignatedIndex"),
    }
    rets = fi.findall(".//n:monthlyTotReturns/n:monthlyTotReturn", NS)
    if rets:  # first class (ETFs have one)
        for k in ("rtn1", "rtn2", "rtn3"):
            s[k] = _f(rets[0].get(k))
    for m in (1, 2, 3):
        fl = fi.find(f"n:mon{m}Flow", NS)
        if fl is not None:
            s[f"sales{m}"] = _f(fl.get("sales"))
            s[f"redemp{m}"] = _f(fl.get("redemption"))
            s[f"reinv{m}"] = _f(fl.get("reinvestment"))
    holdings = []
    for inv in root.findall(".//n:formData/n:invstOrSecs/n:invstOrSec", NS):
        h = {
            "accession": accession,
            "name": _text(inv, "n:name"), "title": _text(inv, "n:title"),
            "cusip": _text(inv, "n:cusip"),
            "balance": _f(_text(inv, "n:balance")), "units": _text(inv, "n:units"),
            "val_usd": _f(_text(inv, "n:valUSD")), "pct_val": _f(_text(inv, "n:pctVal")),
            "payoff": _text(inv, "n:payoffProfile"), "asset_cat": _text(inv, "n:assetCat"),
        }
        isin = inv.find("n:identifiers/n:isin", NS)
        tick = inv.find("n:identifiers/n:ticker", NS)
        h["isin"] = isin.get("value") if isin is not None else None
        h["ticker"] = tick.get("value") if tick is not None else None
        d = inv.find("n:derivativeInfo", NS)
        if d is not None and len(d):
            dv = d[0]
            h["deriv_cat"] = dv.get("derivCat")
            h["notional"] = _f(_text(dv, "n:notionalAmt"))
            h["ref_name"] = _text(dv, ".//n:descRefInstrmnt//n:issuerName") or _text(
                dv, ".//n:descRefInstrmnt//n:indexName")
            rt = dv.find(".//n:descRefInstrmnt//n:identifiers/n:ticker", NS)
            h["ref_ticker"] = rt.get("value") if rt is not None else None
            ri = dv.find(".//n:descRefInstrmnt//n:identifiers/n:isin", NS)
            h["ref_isin"] = ri.get("value") if ri is not None else None
        holdings.append(h)
    return s, holdings


def load_filing(href: str, accession: str):
    xml = fetch(primary_doc_url(href), allow_404=True)
    if not xml:
        return None, []
    try:
        return parse_nport(xml, accession)
    except ET.ParseError:
        return None, []
