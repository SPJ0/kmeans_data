# Phase A2 recorders (free data collection)

Two recorders collect data that doesn't exist historically for free. After about a quarter,
their output supports an out-of-sample re-test of the 2026 effect and the A2 calibration:
how much predicted flow actually shows up in the closing auction.

| Recorder | What it saves | Where it runs | Cost |
|---|---|---|---|
| `recorders/holdings.py` | Each active single-stock lev ETF's holdings: swap notionals, net assets, shares outstanding. This gives the exact prior-close exposure E<sub>t−1</sub> instead of L×A. | GitHub Actions, every weekday at 8:15 ET (`.github/workflows/holdings.yml`), or any machine | Free |
| `recorders/imbalance_recorder.py` | 3:44 pm ranking of every underlying by predicted flow, then 1-second + event-level closing-auction data (auction price, volume, imbalance, regulatory imbalance) for the top ~90 names until 4:01 pm. Optional IB imbalance scanners and 1-minute bars. | Your machine, next to TWS / IB Gateway | Free with the market data you already have. See the note below |

Neither recorder places orders. The IBKR connection is opened **read-only**.

## 1. Holdings scraper

```bash
python -m recorders.holdings                      # all active funds in universe/single_stock_universe.csv
python -m recorders.holdings --tickers TSLL MSTU  # a subset
```
Output goes to `data/holdings/<YYYY-MM-DD>/`: `funds.parquet`, `holdings.parquet`, and `raw/` (native CSV/JSON).

Where exposure comes from:

| Issuer | Source | Exposure in $? |
|---|---|---|
| Direxion | `direxion.com/holdings/<T>.csv` | yes (every swap leg) |
| Defiance | full-holdings table + fund page | yes (weights × net assets) |
| T-REX | fund page holdings block | recorded but **not trusted**: the pages list stale or duplicate swap rows (2.8–5x on some 2x funds), so the model uses L×A |
| GraniteShares | the JSON endpoints their fund page uses | yes |
| KraneShares | dated holdings CSV | yes |
| Tradr, Leverage Shares, ProShares, and any native failure | stockanalysis.com fund page | net assets + shares only. The flow model then uses E = L×A |

Tradr's own data widget is behind reCAPTCHA, so it is not scraped.

First full run (2026-09-23): 292 funds, net assets for all of them, trusted exposure for 135. For those 135, exposure ÷ net assets matched the target leverage within 0.1% for all but one fund (Direxion, 6% off).
The `error` column says why any fund fell back or failed.

**Scheduling.**
- **GitHub Actions:** the workflow runs weekdays at 12:15 UTC and commits the day's folder. GitHub only runs scheduled workflows from the **default branch**, so it starts once this branch is merged. You can also trigger it by hand from the Actions tab ("Run workflow").
- **Blocked runner IPs:** if an issuer blocks GitHub's IPs, the run summary shows it and those funds fall back to stockanalysis. Running locally with cron works too:
  ```cron
  CRON_TZ=America/New_York
  15 8 * * 1-5  cd ~/kmeans_data && .venv/bin/python -m recorders.holdings >> data/holdings.log 2>&1
  ```

**New fund launches** aren't in the universe CSV until it's rebuilt. To pick them up in the
meantime, add them to `universe/extra_funds.csv` (columns `ticker,issuer,underlying,leverage`).

## 2. Closing-imbalance recorder (IBKR)

**Setup (once)**
1. `pip install -r requirements.txt` (includes `ib_async`).
2. Run TWS or IB Gateway, logged into your **live** account. Paper accounts get delayed data.
3. In Configure → API → Settings:
   - enable socket clients
   - socket port 4001 (Gateway) or 7496 (TWS)
   - tick "Read-Only API"
   - add 127.0.0.1 to trusted IPs
4. Keep the Gateway running. [IBC](https://github.com/IbcAlpha/IBC) handles the daily auto-restart and re-login.

**Run**
```bash
python -m recorders.imbalance_recorder --loop --port 4001            # waits for each session, forever
python -m recorders.imbalance_recorder --port 4001 --scanner --bars  # one session, with extras
```
Or schedule the one-shot mode with cron (the script sleeps until the right time):
```cron
CRON_TZ=America/New_York
30 15 * * 1-5  cd ~/kmeans_data && .venv/bin/python -m recorders.imbalance_recorder --port 4001 --scanner >> data/imbalance.log 2>&1
```
Early closes and holidays are read from IBKR's own trading-hours data, so the schedule shifts automatically.

**Before it runs each day:** it needs the latest `data/holdings/<date>/funds.parquet`.
- If the scraper runs on GitHub, `git pull` first; e.g. `cd ~/kmeans_data && git pull -q && .venv/bin/python -m ...` in the cron line.
- Otherwise it falls back to the cached AUM.

Output goes to `data/imbalance/<YYYY-MM-DD>/`:
- `ranking.parquet`: all underlyings with r at close−16m, predicted flow (holdings-based E where available), Gamma, FlowRatio, and which names were selected.
- `ticks.parquet`: every update plus a 1 s heartbeat for the selected names, with last/bid/ask/volume/close and `auctionVolume`, `auctionPrice`, `auctionImbalance`, `regulatoryImbalance`.
- `scanner.parquet`, `bars.parquet`: optional.
- `meta.json`: settings, selected names, contracts that didn't qualify, and errors.

`data/imbalance/` is gitignored (a few MB per day). Remove that line from `.gitignore` if you want the recordings in the repo.

**Market data note: please check before relying on it.** The auction fields come from IBKR generic tick 225 and need **live** US equity quotes on the account.
- I can't verify from here which of your current subscriptions provide them.
- The recorder never changes subscriptions. If none of the auction fields arrive, `meta.json` records:
  `"no auction fields received - check live US equity market data permissions for generic tick 225"`
- Check Client Portal → Settings → Market Data Subscriptions. Don't buy anything until you've decided to.
- Line limit: accounts get 100 simultaneous market-data lines by default. The ranking pass streams names in batches under `--max-lines` (default 90). Lower it if you use lines elsewhere at the same time.

## What to do with the data (later)
- **Calibration:** predicted flow (from `ranking.parquet`) against the published imbalance at 3:50/3:55 and the final imbalance (`ticks.parquet`). This measures the share of flow that reaches the close.
- **Re-test:** redo the Phase A1 reversal test on the recorded days, with holdings-based E and the 3:44 flow estimate you could actually know live.
