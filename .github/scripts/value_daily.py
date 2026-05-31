import os
import sys
import time
import pandas as pd
import yfinance as yf
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from index_management.valuation.Manager import Valuation
from index_management.utilities.utils import fullpath, get_datestr
from datetime import datetime, timedelta

today = datetime.today()
value = Valuation(today, "cw")

df_num_shares = pd.read_csv(fullpath(value.folder_path_quarterly, get_datestr(value.previous_quarter) + ".csv"))
symbol = df_num_shares["Symbol"].to_list()

start = (today - timedelta(days=7)).strftime("%Y-%m-%d")
end = (today + timedelta(days=1)).strftime("%Y-%m-%d")

frames = []
failed = []

for i, ticker in enumerate(symbol):
    print(f"[{i+1}/{len(symbol)}] {ticker}", end=" ", flush=True)
    for attempt in range(3):
        try:
            data = yf.download(ticker, start=start, end=end,
                               interval="1d", auto_adjust=True, progress=False)
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
    print(f"Warning: {len(failed)} tickers skipped: {failed}")

if not frames:
    print("No market data — rate limited or no data available.")
    sys.exit(0)

market_data = pd.concat(frames, axis=1).reindex(columns=symbol)
market_data = market_data.dropna(how="all")

if market_data.empty:
    print("No usable market data.")
    sys.exit(0)

prices = np.array(market_data.ffill().fillna(0).values, dtype=float)
num_shares = np.array(df_num_shares["NumShares"].values, dtype=float)

portfolio_value = prices @ num_shares
df_out = pd.DataFrame(portfolio_value.flatten(), columns=["Portfolio"])
df_out.index = market_data.index.date

for d in range(len(df_out)):
    val = df_out.iloc[d, 0]
    if np.isnan(val) or val <= 0:
        continue
    date_str = df_out.iloc[d].name.strftime("%Y%m%d")
    fname = fullpath("data", "valuation", "daily", "cw", date_str + ".csv")
    df_out.iloc[[d]].to_csv(fname, index=False, header=False)
    print(fname)
