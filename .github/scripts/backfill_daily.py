"""
Backfills daily portfolio valuations from the day after the last existing
valuation file up to today. Downloads prices in a single batch.
"""
import os
import sys
import glob
import pandas as pd
import yfinance as yf
import numpy as np
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from index_management.valuation.Manager import Valuation
from index_management.utilities.utils import fullpath, get_datestr, checkpath

today = datetime.today()
value = Valuation(today, "cw")

# find last existing daily valuation file
daily_dir = fullpath("data", "valuation", "daily", "cw")
checkpath(daily_dir)
existing = sorted(glob.glob(os.path.join(daily_dir, "????????.csv")))

# find the last file that contains a valid positive number (skip empty/rate-limited files)
last_date = None
for f in reversed(existing):
    try:
        val = float(pd.read_csv(f, header=None).iloc[0, 0])
        if val > 0:
            last_date = datetime.strptime(os.path.basename(f).replace(".csv", ""), "%Y%m%d")
            break
    except Exception:
        continue

if last_date:
    start_date = last_date + timedelta(days=1)
else:
    start_date = datetime(2024, 1, 1)

print(f"Backfilling from {start_date.date()} to {today.date()}")

if start_date.date() >= today.date():
    print("Already up to date.")
    sys.exit(0)

# load share counts from the most recent quarterly allocation
df_num_shares = pd.read_csv(fullpath(value.folder_path_quarterly, get_datestr(value.previous_quarter) + ".csv"))
symbol = df_num_shares["Symbol"].to_list()

# download one ticker at a time to avoid rate limiting
import time
frames = []
start_str = start_date.strftime("%Y-%m-%d")
end_str = (today + timedelta(days=1)).strftime("%Y-%m-%d")
failed = []

for i, ticker in enumerate(symbol):
    print(f"[{i+1}/{len(symbol)}] {ticker}", end=" ", flush=True)
    for attempt in range(3):
        try:
            data = yf.download(
                ticker,
                start=start_str,
                end=end_str,
                interval="1d",
                auto_adjust=True,
                progress=False,
            )
            close = data[["Close"]].rename(columns={"Close": ticker})
            frames.append(close)
            print("OK")
            break
        except Exception as e:
            print(f"attempt {attempt+1} failed: {e}", end=" ", flush=True)
            time.sleep(20)
    else:
        print("SKIPPED")
        failed.append(ticker)
    time.sleep(15)

if failed:
    print(f"\nWarning: {len(failed)} tickers skipped: {failed}")

if not frames:
    print("No market data returned.")
    sys.exit(0)

market_data = pd.concat(frames, axis=1)
market_data = market_data.dropna(how="all")

if market_data.empty:
    print("No market data returned.")
    sys.exit(0)

# reorder columns to match share count order, filling missing tickers with 0
market_data = market_data.reindex(columns=symbol, fill_value=np.nan)

# forward-fill intra-series gaps, then zero out tickers with no data at all
market_data = market_data.ffill()
missing = market_data.columns[market_data.isna().all()].tolist()
if missing:
    print(f"Warning: no price data for {missing} — treating as 0")
    market_data[missing] = 0.0
    df_num_shares.loc[df_num_shares["Symbol"].isin(missing), "NumShares"] = 0.0

prices = np.array(market_data.values, dtype=float)
num_shares = np.array(df_num_shares["NumShares"].values, dtype=float)

if prices.shape[1] != num_shares.shape[0]:
    print(f"Shape mismatch: prices {prices.shape}, shares {num_shares.shape}")
    sys.exit(1)

portfolio_value = prices @ num_shares
df_portfolio_value = pd.DataFrame(portfolio_value.flatten(), columns=["Portfolio"])
df_portfolio_value.index = market_data.index.date

written = 0
for d in range(len(df_portfolio_value)):
    date_str = df_portfolio_value.iloc[d].name.strftime("%Y%m%d")
    fname = fullpath(daily_dir, date_str + ".csv")
    df_portfolio_value.iloc[[d]].to_csv(fname, index=False, header=False)
    print(fname)
    written += 1

print(f"\nWrote {written} daily valuation files.")
