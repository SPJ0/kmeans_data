"""EDGAR helpers: N-PORT filing lists per fund series (cached)."""
from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

from common.http import fetch

BROWSE = ("https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={sid}"
          "&type=NPORT-P&dateb=&owner=include&count=100&output=atom")


def nport_filings(series_id: str) -> pd.DataFrame:
    """All NPORT-P (and /A) filings for a series: accession, filing date, href."""
    body = fetch(BROWSE.format(sid=series_id), allow_404=True)
    if not body:
        return pd.DataFrame(columns=["series_id", "accession", "filing_date", "form", "href"])
    txt = body.decode("utf-8", "replace")
    rows = []
    for entry in re.findall(r"<entry>(.*?)</entry>", txt, re.S):
        acc = re.search(r"<accession-number>([^<]+)", entry)
        fdt = re.search(r"<filing-date>([^<]+)", entry)
        typ = re.search(r"<filing-type>([^<]+)", entry)
        href = re.search(r"<filing-href>([^<]+)", entry)
        if acc and fdt and typ and typ.group(1).startswith("NPORT-P"):
            rows.append((series_id, acc.group(1), fdt.group(1), typ.group(1), href.group(1)))
    return pd.DataFrame(rows, columns=["series_id", "accession", "filing_date", "form", "href"])


def nport_filings_many(series_ids, workers: int = 4) -> pd.DataFrame:
    with ThreadPoolExecutor(workers) as ex:
        parts = list(ex.map(nport_filings, series_ids))
    parts = [p for p in parts if len(p)]
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(
        columns=["series_id", "accession", "filing_date", "form", "href"])


def primary_doc_url(href: str) -> str:
    return re.sub(r"/[^/]+-index\.htm$", "/primary_doc.xml", href)
