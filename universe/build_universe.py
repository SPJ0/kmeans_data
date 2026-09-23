"""Build the leveraged/inverse ETF universe from SEC data (closed funds included).

Sources
  * SEC Investment Company Series & Class files, 2022-2026: every registered
    series name and class ticker, including funds that later closed.
  * EDGAR N-PORT-P filings per series: proves the fund launched, gives its life
    span, final-filing flag and the fund's own designated reference instrument.
  * SEC company_tickers_mf.json: currently active fund series -> ticker.

Outputs
  universe/single_stock_universe.csv   single-stock leveraged/inverse funds
  universe/index_universe.csv          index/sector leveraged funds (secondary check)
  universe/rejected_candidates.csv     parsed-but-excluded names with reason
  data/cache/nport_filings.parquet     filing index for launched candidates
"""
from __future__ import annotations

import json
import re

import pandas as pd

from common.paths import CACHE, RAW, UNIVERSE
from flows.nport_bulk import load_funds, load_holdings
from flows.nport_recent import extract_recent
from universe.parse_names import parse_name

YEARS = [2022, 2023, 2024, 2025, 2026]
NAME_PAT = r"(?:\d(?:\.\d+)?\s*x\b|Bull|Bear|Inverse|Short|Leveraged|Ultra|Daily Target)"

# Company names / stale tickers used in older fund names -> current Yahoo ticker
ALIAS = {
    "NVIDIA": "NVDA", "TESLA": "TSLA", "ALPHABET": "GOOGL", "APPLE": "AAPL", "MICROSOFT": "MSFT",
    "AMAZON": "AMZN", "META": "META", "BRKB": "BRK-B", "BRK.B": "BRK-B", "BRK": "BRK-B",
    "Moderna": "MRNA", "Peloton": "PTON", "Tilray": "TLRY", "TWTR": "TWTR", "NKLA": "NKLA",
    "SQ": "XYZ", "FB": "META", "Kick BRK": "BRK-B", "COINBASE": "COIN", "PALANTIR": "PLTR",
    "MICROSTRATEGY": "MSTR", "NETFLIX": "NFLX", "BOEING": "BA", "PFIZER": "PFE", "NIKE": "NKE",
    "Advanced Micro Devices": "AMD", "AMD": "AMD", "BROADCOM": "AVGO", "Intel": "INTC",
}
# Underlyings that are single companies but not US exchange-listed (no US closing auction)
NON_US_LISTED = re.compile(
    r"hynix|samsung|kioxia|lasertec|advantest|hanmi|hyundai|disco\b|besi|mediatek|delta electronics|"
    r"tokyo electron|xiaomi|tencent|softbank|nintendo|metaplanet|fujikura|infineon|schneider|siemens|simens|"
    r"hanwha|leeno|sk square|minimax|sivers|kodex|BYDDY|LYSDY|RYCEY|SSNLF|KRKNF|SIVEF|SIVE\b|BE Semiconductor",
    re.I)
PRIVATE_CO = re.compile(
    r"spacex|openai|anthropic|anduril|databricks|stripe|revolut|kraken|discord|dataiku|roze|lambda|"
    r"cerebras|groq|croq|sambanova|scale ai|nscale|relativity|axiom space|sierra space|applied intuition|"
    r"viva republica|toss|celonis|crusoe|oura|vast data|quantinuum|ledger|plaid|strava|bytedance|shein|"
    r"figure ai|x-energy|sb energy|cohere|plusai",
    re.I)
CRYPTO_COMMOD = re.compile(
    r"bitcoin|ether|solana|xrp|doge|sui\b|hype\b|bnb|cardano|chainlink|stellar|avalanche|bonk|ada\b|sol\b|"
    r"trump|xdc|gold|silver|copper|platinum|palladium|oil|natural gas|corn|wheat|soybean|sugar|uranium|"
    r"crypto|blockchain|ETHM|SOLZ|ETHU|BITX",
    re.I)


# ticker-shaped tokens that are ETFs/indices (not in the SEC operating-company list)
KNOWN_INDEX = {"TIPS", "MAGMA", "FAANG", "QQQQ", "MTVE", "SILJ", "DRAM", "MAGS", "IVES", "GDX", "GDXJ", "GLD",
               "SPY", "QQQ", "IWM", "XLK", "XLF", "XLE", "SOXX", "SMH", "XBI", "ARKK", "TLT", "KWEB", "FXI", "MSOS"}


def load_series_class() -> pd.DataFrame:
    parts = []
    for y in YEARS:
        d = pd.read_csv(RAW / "sec" / f"series_class_{y}.csv", dtype=str, encoding="utf-8-sig",
                        encoding_errors="replace")
        d["year"] = y
        parts.append(d)
    d = pd.concat(parts, ignore_index=True)
    d = d.rename(columns={"Series ID": "series_id", "Series Name": "series_name",
                          "Class Ticker": "class_ticker", "Entity Name": "trust",
                          "CIK Number": "trust_cik", "Class ID": "class_id"})
    d["series_name"] = d["series_name"].str.replace("&amp;", "&", regex=False)
    d["class_ticker"] = d["class_ticker"].replace("[NULL]", pd.NA)
    return d


def stock_ticker_sets():
    ex = json.load(open(RAW / "sec" / "company_tickers_exchange.json"))
    df = pd.DataFrame(ex["data"], columns=ex["fields"])
    fundlike = df["name"].str.contains(r"\bETF\b|\bTRUST\b|\bFUND\b|ISHARES|SPDR|PROSHARES|INVESCO QQQ",
                                       case=False, regex=True)
    stocks = set(df.loc[~fundlike, "ticker"].str.replace(".", "-", regex=False))
    mf = json.load(open(RAW / "sec" / "company_tickers_mf.json"))
    mf = pd.DataFrame(mf["data"], columns=mf["fields"])
    funds = set(df.loc[fundlike, "ticker"]) | set(mf["symbol"])
    return stocks, funds, mf


def classify(token: str | None, stocks: set, funds: set) -> tuple[str, str | None]:
    """-> (kind, underlying_ticker). kind in stock / index / nonus_stock / private / crypto_commod / unknown."""
    if not isinstance(token, str) or not token:
        return "unknown", None
    t = token.strip("[]").strip()
    alias = {k.upper(): v for k, v in ALIAS.items()}
    if t.upper() in alias:
        return "stock", alias[t.upper()]
    tu = t.upper().replace(".", "-")
    if PRIVATE_CO.search(t):
        return "private", None
    if NON_US_LISTED.search(t):
        return "nonus_stock", None
    if CRYPTO_COMMOD.search(t) and (tu not in stocks or t != t.upper()):
        return "crypto_commod", None
    if tu in stocks and tu not in funds:
        return "stock", tu
    if tu in KNOWN_INDEX:
        return "index", None
    if tu in funds or " " in t or not re.fullmatch(r"[A-Z][A-Z0-9\-]{0,5}", t):
        return "index", None
    # ticker-shaped token not in the current SEC list: delisted / renamed / new listing
    return "stock_unverified", tu


def stock_names() -> dict:
    ex = json.load(open(RAW / "sec" / "company_tickers_exchange.json"))
    return {r[2].replace(".", "-"): r[1] for r in ex["data"]}


_GENERIC = {"INC", "CORP", "CORPORATION", "CO", "LTD", "PLC", "HOLDINGS", "HOLDING", "GROUP", "THE", "CLASS", "COM",
            "COMMON", "STOCK", "SHS", "ADR", "SA", "NV", "AG", "SE", "TRS", "EQ", "SWAP", "TOTAL", "RETURN",
            "LIMITED", "COMPANY", "TECHNOLOGIES", "TECHNOLOGY", "&", "AND", "DE", "NEW", "US", "EQUITY"}


def _words(s: str) -> set:
    return {w for w in re.findall(r"[A-Z0-9]+", str(s).upper()) if w not in _GENERIC and len(w) > 1}


def nport_reference(nf: pd.DataFrame) -> pd.DataFrame:
    """Largest non-cash exposure in the fund's most recent filing, as a readable string."""
    h = load_holdings()
    last = nf.sort_values("report_date").groupby("series_id")["accession_number"].last()
    h = h[h["accession_number"].isin(set(last))]
    h = h[~h["asset_cat"].isin(["STIV", "DBT"]) & ~h["issuer_title"].fillna("").str.contains(
        r"TREASUR|MONEY MARKET|GOVT|CASH|FIRST AMERICAN|DREYFUS|FIDELITY INST|GOLDMAN SACHS FIN", case=False)]
    h = h.assign(size=h["notional_amount"].abs().fillna(0) + h["currency_value"].abs().fillna(0))
    rows = {}
    acc2sid = {a: s for s, a in last.items()}
    for acc, g in h.groupby("accession_number"):
        top = g.sort_values("size", ascending=False).head(3)
        parts = []
        for _, r in top.iterrows():
            bits = [r.get("ref_ticker"), r.get("identifier_ticker"), r.get("ref_name"), r.get("ref_title"),
                    r.get("issuer_name"), r.get("issuer_title")]
            parts.append(" / ".join(str(b) for b in bits if isinstance(b, str) and b not in ("N/A", "None", "nan")))
        rows[acc2sid[acc]] = " || ".join(dict.fromkeys(parts))
    ref = pd.Series(rows, name="nport_ref")
    di = nf.sort_values("report_date").groupby("series_id")["designated_index_name"].last()
    return pd.concat([ref, di.rename("nport_designated_index")], axis=1)


NAME_ALIASES = {"GOOGL": ["GOOGLE", "ALPHABET"], "GOOG": ["GOOGLE", "ALPHABET"], "UNH": ["UNITED HEALTH"],
                "XOM": ["EXXON"], "BRK-B": ["BERKSHIRE"], "META": ["FACEBOOK", "META"], "XYZ": ["BLOCK", "SQUARE"],
                "MSTR": ["MICROSTRATEGY", "STRATEGY"]}


def ref_match(underlying, ref, names: dict) -> str:
    if not isinstance(underlying, str):
        return "n/a"
    if not isinstance(ref, str) or not ref:
        return "no_ref"
    tokens = set(re.findall(r"[A-Z0-9]+", ref.upper()))
    if any(a in ref.upper() for a in NAME_ALIASES.get(underlying, [])):
        return "ok_name"
    tick = underlying.replace("-", "")
    if tick in tokens or underlying.split("-")[0] in tokens and len(underlying) > 2:
        return "ok_ticker"
    nm = _words(names.get(underlying, ""))
    if nm and nm & _words(ref):
        return "ok_name"
    if not nm:
        return "unverified_no_sec_name"
    return "MISMATCH"


def drop_misfiled(nf: pd.DataFrame) -> pd.DataFrame:
    """Drop filings that exactly duplicate another series' report (same date, same net assets
    to the cent) - e.g. MSTZ's Nov-2024 report was also filed under a sibling series. The copy
    from the series with fewer filings is dropped."""
    n_by_series = nf.groupby("series_id")["accession_number"].transform("size")
    nf = nf.assign(_n=n_by_series, _na=nf["net_assets"].round(2))
    dup = nf.duplicated(["report_date", "_na"], keep=False) & nf["_na"].gt(0)
    keep = ~dup | (nf.groupby(["report_date", "_na"])["_n"].transform("max") == nf["_n"])
    dropped = nf[~keep]
    if len(dropped):
        print("dropping misfiled duplicate filings:", dropped[["series_id", "series_name", "report_date"]].values.tolist())
    return nf[keep].drop(columns=["_n", "_na"])


def build() -> None:
    sc = load_series_class()
    cand = sc[sc["series_name"].fillna("").str.contains(NAME_PAT, case=False, regex=True)]
    stocks, funds, mf = stock_ticker_sets()

    # one row per series: latest name, all names seen (leverage-change history), latest ticker
    cand = cand.sort_values("year")
    g = cand.groupby("series_id")
    ser = pd.DataFrame({
        "series_name": g["series_name"].last(),
        "names_by_year": g.apply(lambda x: "; ".join(f"{y}:{n}" for y, n in
                                                     x.drop_duplicates("series_name")[["year", "series_name"]].values),
                                 include_groups=False),
        "trust": g["trust"].last(), "trust_cik": g["trust_cik"].last(),
        "sc_ticker": g["class_ticker"].agg(lambda x: x.dropna().iloc[-1] if x.notna().any() else pd.NA),
        "sc_first_year": g["year"].min(), "sc_last_year": g["year"].max(),
    }).reset_index()
    cur = mf.groupby("seriesId")["symbol"].first()
    ser["current_ticker"] = ser["series_id"].map(cur)
    ser["ticker"] = ser["current_ticker"].fillna(ser["sc_ticker"])
    ser["listed_now"] = ser["current_ticker"].notna()

    nport_names = (load_funds().sort_values("report_date").groupby("series_id")["series_name"].last())
    ser["sc_series_name"] = ser["series_name"]
    ser["series_name"] = ser["series_id"].map(nport_names).fillna(ser["series_name"])
    parsed = ser["series_name"].map(parse_name)
    for f in ("issuer", "leverage", "reset", "underlying_token", "excluded_reason"):
        ser[f] = [getattr(p, f) for p in parsed]
    # leverage history from every name the series carried
    ser["leverage_history"] = ser["names_by_year"].map(
        lambda s: "; ".join(f"{part.split(':', 1)[0]}:{parse_name(part.split(':', 1)[1]).leverage}"
                            for part in s.split("; ")))
    kinds = [classify(t, stocks, funds) for t in ser["underlying_token"]]
    ser["kind"] = [k for k, _ in kinds]
    ser["underlying"] = [u for _, u in kinds]

    keep = ser["excluded_reason"].isna() & ser["kind"].isin(["stock", "stock_unverified", "index"])
    rej = ser[~keep].copy()
    rej["reject_reason"] = rej["excluded_reason"].fillna("underlying_" + rej["kind"])
    work = ser[keep].copy()

    # launched? -> the fund filed N-PORT reports with positive net assets
    if not (CACHE / "nport" / "funds_edgar_recent.parquet").exists():
        extract_recent(work["trust_cik"].unique(), after="2026-07-01", series_keep=set(work["series_id"]))
    nf = load_funds()
    nf = nf[nf["series_id"].isin(set(work["series_id"]))]
    nf = nf.sort_values(["series_id", "report_date", "filing_date"]).drop_duplicates(
        ["series_id", "report_date"], keep="last")          # amendments supersede originals
    nf = drop_misfiled(nf)
    nf.to_parquet(CACHE / "nport_universe_filings.parquet", index=False)
    pos = nf[nf["net_assets"] > 0]
    life = pos.groupby("series_id").agg(
        n_nport=("accession_number", "size"), first_report=("report_date", "min"),
        last_report=("report_date", "max"), last_net_assets=("net_assets", "last"),
        max_net_assets=("net_assets", "max"),
        final_filing=("is_last_filing", lambda x: (x.astype(str).str.upper() == "Y").any()))
    work = work.join(life, on="series_id")
    work["n_nport"] = work["n_nport"].fillna(0).astype(int)
    work["launched_evidence"] = pd.Series(pd.NA, index=work.index, dtype="object")
    work.loc[work["n_nport"] > 0, "launched_evidence"] = "nport"
    work.loc[(work["n_nport"] == 0) & work["listed_now"], "launched_evidence"] = "listed_no_nport_yet"
    work["status"] = "active"
    work.loc[~work["listed_now"] | work["final_filing"].fillna(False).astype(bool), "status"] = "closed"

    never = work[work["launched_evidence"].isna()].copy()
    never["reject_reason"] = "never_launched_or_no_filings"
    rej = pd.concat([rej, never])
    work = work[work["launched_evidence"].notna()].copy()
    work = work.join(nport_reference(nf), on="series_id")
    names = stock_names()
    work["ref_match"] = [ref_match(u, r, names) for u, r in zip(work["underlying"], work["nport_ref"])]

    cols = ["ticker", "issuer", "underlying", "leverage", "reset", "status", "series_id", "series_name",
            "trust", "trust_cik", "kind", "underlying_token", "listed_now", "n_nport", "first_report",
            "last_report", "last_net_assets", "max_net_assets", "launched_evidence", "nport_ref", "ref_match",
            "nport_designated_index",
            "leverage_history", "names_by_year"]
    single = work[work["kind"].isin(["stock", "stock_unverified"])][cols].sort_values(["underlying", "leverage"])
    index = work[work["kind"] == "index"][cols].sort_values(["underlying_token", "leverage"])
    UNIVERSE.mkdir(exist_ok=True)
    single.to_csv(UNIVERSE / "single_stock_candidates.csv", index=False)
    index.to_csv(UNIVERSE / "index_candidates.csv", index=False)
    rej[["series_id", "series_name", "trust", "reject_reason", "leverage", "reset", "underlying_token"]].to_csv(
        UNIVERSE / "rejected_candidates.csv", index=False)
    print(f"series scanned={len(ser)} single-stock launched={len(single)} index launched={len(index)} "
          f"rejected={len(rej)}")


if __name__ == "__main__":
    build()
