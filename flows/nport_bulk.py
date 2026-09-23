"""Extract leveraged-fund rows from SEC DERA quarterly N-PORT data sets.

Each quarterly zip (~450 MB, keyed by *filing* quarter) is downloaded once to
data/raw/nport_zip/ and reduced to compact parquet files in data/cache/nport/:

  funds_<q>.parquet     one row per filing: series, report date, net assets,
                        monthly flows (sales/redemptions), monthly returns,
                        designated index
  holdings_<q>.parquet  holdings of those filings with swap notional and the
                        swap's reference instrument (name / ticker / ISIN)

Only series whose name looks leveraged/inverse are kept.
"""
from __future__ import annotations

import csv
import sys
import zipfile

import pandas as pd

from common.http import USER_AGENT
from common.paths import CACHE, RAW

ZIP_DIR = RAW / "nport_zip"
OUT = CACHE / "nport"
URL = "https://www.sec.gov/files/dera/data/form-n-port-data-sets/{q}_nport.zip"
NAME_PAT = r"(?:\d(?:\.\d+)?\s*x\b|Bull|Bear|Inverse|Short|Leveraged|Ultra|Daily Target)"
QUARTERS = [f"{y}q{k}" for y in range(2022, 2027) for k in range(1, 5)
            if "2022q3" <= f"{y}q{k}" <= "2026q2"]
TSV = dict(sep="\t", dtype=str, quoting=csv.QUOTE_NONE, on_bad_lines="skip", encoding_errors="replace")


def _download(q: str):
    import requests
    ZIP_DIR.mkdir(parents=True, exist_ok=True)
    path = ZIP_DIR / f"{q}_nport.zip"
    if path.exists() and zipfile.is_zipfile(path):
        return path
    tmp = path.with_suffix(".part")
    with requests.get(URL.format(q=q), headers={"User-Agent": USER_AGENT}, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(1 << 22):
                f.write(chunk)
    tmp.replace(path)
    return path


def _read(z: zipfile.ZipFile, name: str, **kw) -> pd.DataFrame:
    with z.open(name) as fh:
        return pd.read_csv(fh, **TSV, **kw)


def _read_filtered(z, name, key, keep: set, usecols=None, chunksize=2_000_000) -> pd.DataFrame:
    parts = []
    with z.open(name) as fh:
        for ch in pd.read_csv(fh, **TSV, usecols=usecols, chunksize=chunksize):
            parts.append(ch[ch[key].isin(keep)])
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=usecols)


def extract_quarter(q: str, force: bool = False) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    f_out, h_out = OUT / f"funds_{q}.parquet", OUT / f"holdings_{q}.parquet"
    if f_out.exists() and h_out.exists() and not force:
        return
    path = _download(q)
    with zipfile.ZipFile(path) as z:
        sub = _read(z, "SUBMISSION.tsv")
        fri = _read(z, "FUND_REPORTED_INFO.tsv")
        fri = fri[fri["SERIES_NAME"].fillna("").str.contains(NAME_PAT, case=False, regex=True)]
        cols = ["ACCESSION_NUMBER", "SERIES_NAME", "SERIES_ID", "TOTAL_ASSETS", "TOTAL_LIABILITIES",
                "NET_ASSETS"] + [c for c in fri.columns if "_FLOW_MON" in c]
        fri = fri[cols]
        acc = set(fri["ACCESSION_NUMBER"])
        mtr = _read(z, "MONTHLY_TOTAL_RETURN.tsv")
        mtr = mtr[mtr["ACCESSION_NUMBER"].isin(acc)].drop_duplicates("ACCESSION_NUMBER")
        var = _read(z, "FUND_VAR_INFO.tsv")
        var = var[var["ACCESSION_NUMBER"].isin(acc)].drop_duplicates("ACCESSION_NUMBER")
        funds = (fri.merge(sub, on="ACCESSION_NUMBER", how="left")
                 .merge(mtr[["ACCESSION_NUMBER", "CLASS_ID", "MONTHLY_TOTAL_RETURN1", "MONTHLY_TOTAL_RETURN2",
                             "MONTHLY_TOTAL_RETURN3"]], on="ACCESSION_NUMBER", how="left")
                 .merge(var[["ACCESSION_NUMBER", "DESIGNATED_INDEX_NAME"]], on="ACCESSION_NUMBER", how="left"))
        funds.columns = [c.lower() for c in funds.columns]
        funds["dataset_quarter"] = q

        hcols = ["ACCESSION_NUMBER", "HOLDING_ID", "ISSUER_NAME", "ISSUER_TITLE", "ISSUER_CUSIP", "BALANCE", "UNIT",
                 "CURRENCY_VALUE", "PERCENTAGE", "PAYOFF_PROFILE", "ASSET_CAT", "DERIVATIVE_CAT"]
        hold = _read_filtered(z, "FUND_REPORTED_HOLDING.tsv", "ACCESSION_NUMBER", acc, usecols=hcols)
        hid = set(hold["HOLDING_ID"])
        ident = _read_filtered(z, "IDENTIFIERS.tsv", "HOLDING_ID", hid,
                               usecols=["HOLDING_ID", "IDENTIFIER_ISIN", "IDENTIFIER_TICKER"])
        ident = ident.drop_duplicates("HOLDING_ID")
        swp = _read(z, "NONFOREIGN_EXCHANGE_SWAP.tsv", usecols=["HOLDING_ID", "NOTIONAL_AMOUNT", "CURRENCY_CODE",
                                                                  "TERMINATION_DATE"])
        swp = swp[swp["HOLDING_ID"].isin(hid)].drop_duplicates("HOLDING_ID")
        ref = _read(z, "DESC_REF_OTHER.tsv", usecols=["HOLDING_ID", "ISSUER_NAME", "ISSUE_TITLE", "CUSIP", "ISIN",
                                                       "TICKER"])
        ref = ref[ref["HOLDING_ID"].isin(hid)].drop_duplicates("HOLDING_ID").rename(
            columns={"ISSUER_NAME": "REF_NAME", "ISSUE_TITLE": "REF_TITLE", "CUSIP": "REF_CUSIP",
                     "ISIN": "REF_ISIN", "TICKER": "REF_TICKER"})
        hold = (hold.merge(ident, on="HOLDING_ID", how="left").merge(swp, on="HOLDING_ID", how="left")
                .merge(ref, on="HOLDING_ID", how="left"))
        hold.columns = [c.lower() for c in hold.columns]
    funds.to_parquet(f_out, index=False)
    hold.to_parquet(h_out, index=False)
    print(q, "filings", len(funds), "holdings", len(hold), flush=True)


def load_funds() -> pd.DataFrame:
    df = pd.concat([pd.read_parquet(p) for p in sorted(OUT.glob("funds_*.parquet"))], ignore_index=True)
    num = [c for c in df.columns if c.startswith(("total_", "net_assets", "sales_", "redemption_", "reinvestment_",
                                                  "monthly_total_return"))]
    df[num] = df[num].apply(pd.to_numeric, errors="coerce")
    for c in ("filing_date", "report_date", "report_ending_period"):
        df[c] = pd.to_datetime(df[c], format="%d-%b-%Y", errors="coerce")
    return df


def load_holdings() -> pd.DataFrame:
    df = pd.concat([pd.read_parquet(p) for p in sorted(OUT.glob("holdings_*.parquet"))], ignore_index=True)
    for c in ("balance", "currency_value", "percentage", "notional_amount"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


if __name__ == "__main__":
    qs = sys.argv[1:] or QUARTERS
    for q in qs:
        extract_quarter(q)
