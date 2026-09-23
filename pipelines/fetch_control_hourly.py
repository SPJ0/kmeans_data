"""Hourly bars for untreated control stocks (600 most volatile with median ADV > $100M, 2024+)."""
import sys

from pipelines.prices import download_hourly

if __name__ == "__main__":
    download_hourly(open(sys.argv[1]).read().split())
