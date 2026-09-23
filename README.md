# Auction-flow strategy research: Phase A1 (leveraged-ETF rebalancing reversal)

Tests whether daily-reset single-stock leveraged/inverse ETF rebalancing flow pushes closing
prices that then revert overnight. Uses free data only (SEC EDGAR, Yahoo).
**Results and verdict: [`reports/PHASE_A1_REPORT.md`](reports/PHASE_A1_REPORT.md).**

## Layout
| Dir | Contents |
|---|---|
| `common/` | paths, polite cached HTTP fetcher (every SEC/issuer response cached under `data/raw/http/`) |
| `universe/` | fund-name parser, universe build from SEC series/class + N-PORT, finalization and verification flags; output CSVs |
| `flows/` | flow math (`flow.py`), N-PORT bulk/recent extraction, asset reconstruction, prices, earnings, current AUM, panel build |
| `analysis/` | Phase A1 statistics (`run_a1.py`) and index-level secondary check |
| `reports/` | tables (CSV), figures (PNG), `summary.json`, the write-up |
| `tests/` | unit tests for the flow formula and asset reconstruction |
| `data/` | caches. Committed: compact parquet snapshots (prices, N-PORT fund rows, fund-days, AUM, earnings). Ignored: raw zips/HTTP cache/derived panel |

## Rerun
```bash
python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
python -m pytest -q tests

# analysis only, from committed caches (no network):
python -m flows.build_panel        # -> data/cache/fund_days.parquet, stock_days.parquet
python -m analysis.run_a1          # -> reports/
python -m analysis.index_check     # -> reports/t9_index_secondary_check.csv

# full rebuild from source (downloads ~7 GB of SEC N-PORT zips once; all cached):
python -m universe.download_sec
python -m flows.nport_bulk         # 2022Q3..2026Q2 DERA data sets -> data/cache/nport/
python -m universe.build_universe  # candidates (+ EDGAR N-PORT filings since 2026-07-01)
python -m flows.prices             # Yahoo OHLCV for universe, benchmarks, placebo pool (cached)
python -m universe.finalize        # -> universe/single_stock_universe.csv, verify_by_hand.csv
```
Current AUM (latest asset anchor) comes from `flows.current_aum.fetch_current(tickers)`; the
committed `data/cache/current_aum.parquet` was fetched 2026-09-23.
Set `SEC_USER_AGENT` to your own "name email" string for SEC requests.
