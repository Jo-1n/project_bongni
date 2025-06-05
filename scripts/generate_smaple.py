import pandas as pd
import numpy as np
from datetime import datetime, timedelta

"""
Generates a sample 1-minute CSV for a single symbol over N minutes.
Useful for testing backtests.

Usage:
  python scripts/generate_sample_csv.py AAPL 2025-06-01 09:30 100
This generates 100 rows starting from 2025-06-01 09:30 in America/New_York time.
"""

import argparse

def main(symbol: str, start_date: str, start_time: str, count: int):
    tz = "America/New_York"
    start_dt = pd.to_datetime(f"{start_date} {start_time}").tz_localize(tz)
    timestamps = [start_dt + timedelta(minutes=i) for i in range(count)]
    open_prices = 100 + np.cumsum(np.random.randn(count)) * 0.5
    high_prices = open_prices + np.abs(np.random.randn(count) * 0.2)
    low_prices  = open_prices - np.abs(np.random.randn(count) * 0.2)
    close_prices = open_prices + np.random.randn(count) * 0.1
    volumes = np.random.randint(100, 1000, count)

    df = pd.DataFrame({
        "datetime": timestamps,
        "open":     open_prices,
        "high":     high_prices,
        "low":      low_prices,
        "close":    close_prices,
        "volume":   volumes
    })
    df.to_csv(f"data/historical/{symbol}_1min_sample.csv", index=False)
    print(f"Generated data/historical/{symbol}_1min_sample.csv with {count} rows.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("symbol", help="Ticker symbol, e.g. AAPL")
    parser.add_argument("start_date", help="YYYY-MM-DD date, e.g. 2025-06-01")
    parser.add_argument("start_time", help="HH:MM time, e.g. 09:30")
    parser.add_argument("count", type=int, help="Number of minutes to generate")
    args = parser.parse_args()
    main(args.symbol, args.start_date, args.start_time, args.count)