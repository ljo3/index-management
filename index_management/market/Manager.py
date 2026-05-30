import os
import pandas as pd
import yfinance as yf
from index_management.utilities.utils import fullpath, checkpath
from index_management.utilities.utils import last_day, last_working_day, validate_date
from index_management.utilities.utils import get_datestr
from index_management.validation.models import MarketConfig
from datetime import timedelta

class Market:
    # Market class manages the daily market data
    # Brings in data from Yahoo Finance
    # stores it under the path data/market/{date}

    def __init__(self, current_date):
        self.inception_date = validate_date("2020-12-31")
        self.current_date = validate_date(current_date)
        self.last_day = last_day(self.current_date)
        self.last_working_day = last_working_day(self.current_date)
        self.interval = "1d"

        # quarters data - to get most recent quarter
        quarters = pd.read_csv(fullpath("data","quarters.txt"), names=["qtr"],  skiprows=1)
        quarters["qtr"] = quarters["qtr"].apply(lambda x: validate_date(x))

        # get prior_weights
        idx = validate_date(self.current_date) > quarters["qtr"]
        if any(idx):
            previous_quarter = max(quarters.loc[idx, "qtr"])
        else:
            previous_quarter = self.current_date

        universe_path = fullpath("data","universe","processed",
                                 get_datestr(previous_quarter)+".csv")

        self.universe = pd.read_csv(universe_path)
        MarketConfig(current_date=self.current_date, universe=self.universe, interval=self.interval)

    def path_market(self,module):
        folder_path = fullpath("data", "market", module)
        checkpath(folder_path)
        return folder_path


    def get_prices(self):

        # get universe
        symbols = list(self.universe.loc[:, "symbol"])
        market_data = yf.download(symbols, start=self.inception_date, end=self.last_working_day+timedelta(days=5), interval=self.interval, group_by="column")
        market_data = market_data.xs("Close", level=0, axis=1)

        # path_market_data
        path_market_data = fullpath( self.path_market("prices"),
                                     get_datestr(self.current_date)+".csv" )
        market_data.to_csv(path_market_data)
        return market_data

    def get_caps(self):

        # get universe
        symbols = list(self.universe.loc[:, "symbol"])

        market_caps = {}
        for symbol in symbols:
            try:
                stock = yf.Ticker(symbol)
                market_cap = stock.info.get("marketCap")
                market_caps[symbol] = market_cap if market_cap else "N/A"
            except Exception as e:
                market_caps[symbol] = f"Error: {e}"

        df_market_caps = pd.DataFrame(list(market_caps.items()), columns=["Symbol", "MarketCap"])

        # path_market_cap
        path_market_data = fullpath( self.path_market("caps"),
                                     get_datestr(self.current_date)+".csv" )
        df_market_caps.to_csv(path_market_data, index=False)
        return df_market_caps

    def get_daily_prices(self):

        # get universe
        symbols = list(self.universe.loc[:, "symbol"])

        # download market data
        market_data = yf.download(symbols, start=self.current_date - timedelta(days=120), end=self.current_date + timedelta(days=3), interval=self.interval, group_by="column")
        market_data = market_data.xs("Close", level=0, axis=1)

        path_market_data = fullpath( self.path_market("prices"),
                                     get_datestr(self.current_date)+".csv" )
        market_data.to_csv(path_market_data)
        return market_data
