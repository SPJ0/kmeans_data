from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW = DATA / "raw"
CACHE = DATA / "cache"          # compact parquet caches (committed)
UNIVERSE = ROOT / "universe"
REPORTS = ROOT / "reports"

for _p in (RAW, CACHE, REPORTS):
    _p.mkdir(parents=True, exist_ok=True)
