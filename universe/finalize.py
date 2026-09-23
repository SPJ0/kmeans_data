"""Finalize the single-stock universe: inclusion rules, dates, status, verification flags.

Checks per fund
  * N-PORT reference instrument vs parsed underlying (build_universe.ref_match)
  * realized leverage: slope of the ETF's daily return on the underlying's
    (|r_u| > 0.2% days), full life and worst quarter, vs the name's leverage
  * ticker recycling: Yahoo history that starts well before the fund's first N-PORT report

Writes universe/single_stock_universe.csv (the file analysis uses; column
``include``) and universe/verify_by_hand.csv (rows with any flag).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from common.paths import CACHE, UNIVERSE
from flows import prices as px

LAST = pd.Timestamp("2026-09-22")


def _beta(f: pd.Series, u: pd.Series):
    d = pd.concat([f.rename("f"), u.rename("u")], axis=1).dropna()
    d = d[(d["u"].abs() > 0.002) & (d["f"].abs() < 0.9)]
    if len(d) < 15:
        return np.nan, np.nan, len(d)
    full = np.polyfit(d["u"], d["f"], 1)[0]
    qs = [np.polyfit(g["u"], g["f"], 1)[0] for _, g in d.groupby(d.index.to_period("Q")) if len(g) >= 15]
    return full, (qs if qs else [np.nan]), len(d)


def finalize() -> pd.DataFrame:
    u = pd.read_csv(UNIVERSE / "single_stock_candidates.csv", parse_dates=["first_report", "last_report"])
    aum_p = CACHE / "current_aum.parquet"
    aum = pd.read_parquet(aum_p).set_index("ticker") if aum_p.exists() else pd.DataFrame()
    rows = []
    for _, f in u.iterrows():
        flags = []
        up = px.load(f["underlying"])
        ep = px.load(f["ticker"]) if isinstance(f["ticker"], str) else None
        r = f.to_dict()
        r["underlying_prices"] = up is not None
        r["etf_prices"] = ep is not None
        r["etf_first_px"] = ep.index.min() if ep is not None else pd.NaT
        r["etf_last_px"] = ep.index.max() if ep is not None else pd.NaT
        if ep is not None and pd.notna(f["first_report"]) and r["etf_first_px"] < f["first_report"] - pd.Timedelta(days=200):
            flags.append("ticker_history_predates_fund(recycled?)")
        # inception: first Yahoo print, else N-PORT-derived (first report quarter)
        r["inception_date"] = r["etf_first_px"] if ep is not None else (
            f["first_report"] - pd.offsets.MonthBegin(3) if pd.notna(f["first_report"]) else pd.NaT)
        # status: trading to the end of the sample on Yahoo -> active
        active = ep is not None and r["etf_last_px"] >= LAST - pd.Timedelta(days=7)
        r["status"] = "active" if active else "closed"
        if not active and ep is not None:
            r["close_date"] = r["etf_last_px"]
        elif not active:
            r["close_date"] = f["last_report"]
        else:
            r["close_date"] = pd.NaT
        # realized leverage
        rb, rq = np.nan, [np.nan]
        if ep is not None and up is not None:
            ec, uc = px.clean(f["ticker"], ep), px.clean(f["underlying"], up)
            rb, rq, n = _beta(ec["r_cc"][~ec["bad_today"]], uc["r_cc"][~uc["bad_today"]])
            r["realized_L_full"], r["realized_L_n"] = rb, n
            r["realized_L_q_min"], r["realized_L_q_max"] = np.nanmin(rq), np.nanmax(rq)
            L = float(f["leverage"])
            if np.isfinite(rb) and (np.sign(rb) != np.sign(L) or abs(rb - L) > 0.35 * max(abs(L), 1)):
                flags.append(f"realized_L={rb:.2f}_vs_{L:g}")
        if isinstance(f["leverage_history"], str) and len({x.split(":")[1] for x in f["leverage_history"].split("; ")}) > 1:
            flags.append("leverage_changed_by_name:" + f["leverage_history"])
        if f["ref_match"] == "MISMATCH":
            flags.append("nport_reference_mismatch")
        if f["ref_match"] == "no_ref" and f["n_nport"] > 0:
            flags.append("nport_without_reference_holding")
        r["current_aum"] = aum["total_assets"].get(f["ticker"], np.nan) if len(aum) and isinstance(f["ticker"], str) else np.nan
        # inclusion
        launched = (f["n_nport"] > 0) or (ep is not None)
        reasons = []
        if not r["underlying_prices"]:
            reasons.append("no_underlying_prices")
        if not launched:
            reasons.append("no_evidence_it_traded(no N-PORT, no Yahoo prices)")
        if f["ref_match"] == "MISMATCH":
            reasons.append("reference_mismatch")
        if f["reset"] != "daily":
            reasons.append("non_daily_reset")
        if np.isfinite(rb) and r.get("realized_L_n", 0) >= 20 and (np.sign(rb) != np.sign(float(f["leverage"]))
                                                                   or abs(rb) < 0.25 * abs(float(f["leverage"]))):
            reasons.append(f"realized_leverage_{rb:.2f}_inconsistent_with_underlying")
        r["include"] = not reasons
        r["exclude_reason"] = "; ".join(reasons)
        r["verify_flags"] = "; ".join(flags)
        rows.append(r)
    out = pd.DataFrame(rows)
    # the same ticker on two series: keep the one with N-PORT history
    dup = out["ticker"].notna() & out.duplicated("ticker", keep=False)
    for t, g in out[dup].groupby("ticker"):
        best = g.sort_values("n_nport", ascending=False).index[0]
        for i in g.index.drop(best):
            out.loc[i, "include"] = False
            out.loc[i, "exclude_reason"] = (out.loc[i, "exclude_reason"] + "; " if out.loc[i, "exclude_reason"]
                                            else "") + f"ticker_{t}_belongs_to_{out.loc[best, 'series_id']}"
    cols = ["ticker", "issuer", "underlying", "leverage", "inception_date", "status", "close_date", "include",
            "exclude_reason", "verify_flags", "leverage_history", "realized_L_full", "realized_L_q_min",
            "realized_L_q_max", "realized_L_n", "series_id", "series_name", "trust", "trust_cik", "reset",
            "n_nport", "first_report", "last_report", "last_net_assets", "max_net_assets", "current_aum",
            "etf_prices", "etf_first_px", "etf_last_px", "ref_match", "nport_ref", "nport_designated_index",
            "names_by_year"]
    out = out[cols].sort_values(["include", "underlying", "leverage"], ascending=[False, True, False])
    out.to_csv(UNIVERSE / "single_stock_universe.csv", index=False)
    out[(out["verify_flags"] != "") & out["include"]].to_csv(UNIVERSE / "verify_by_hand.csv", index=False)
    inc = out[out["include"]]
    print(f"included funds={len(inc)} (active {int((inc.status == 'active').sum())}, closed "
          f"{int((inc.status == 'closed').sum())}), underlyings={inc['underlying'].nunique()}, "
          f"flagged={int((inc.verify_flags != '').sum())}; excluded={int((~out.include).sum())}")
    return out


if __name__ == "__main__":
    finalize()
