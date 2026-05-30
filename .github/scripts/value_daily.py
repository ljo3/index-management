import pandas as pd
import yfinance as yf
import numpy as np
from index_management.valuation.Manager import Valuation
from index_management.utilities.utils import fullpath, get_datestr
from datetime import datetime, timedelta


today = datetime.today()
value = Valuation(today,"cw")

t1 = timedelta(days=1)

current_quarter = fullpath(value.folder_path_quarterly, today.strftime("%Y%m%d")+".csv")
df_num_shares = pd.read_csv(fullpath( value.folder_path_quarterly, get_datestr(value.previous_quarter)+".csv" ))

symbol = df_num_shares["Symbol"].to_list()

market_data = yf.download(symbol, start=today-t1*7, end=today, interval="1d", group_by="column", auto_adjust=True) 
market_data = market_data.xs("Close",level=0, axis=1)

try:
    # check market data and symbol alignment
    if all(market_data.columns == symbol):
        prices = np.matrix( market_data.values )
        num_shares = np.matrix(df_num_shares["NumShares"]).transpose()

        # check inner size of matrix prior to multiplication
        if prices.shape[1] == num_shares.shape[0]:
            portfolio_value = prices @ num_shares
            df_portfolio_value = pd.DataFrame(portfolio_value, columns=["Portfolio"])
            df_portfolio_value.index = market_data.index.date

            # publish daily portfolio value
            for d in range(len(df_portfolio_value)):
                current_dte = df_portfolio_value.iloc[d,:].name.strftime("%Y%m%d")
                fname = fullpath("data","valuation","daily","cw",current_dte+".csv")
                df_portfolio_value.iloc[[d]].to_csv(fname, index=False,header=False)
                print(fname)

except:
    print("nothing to commit")
