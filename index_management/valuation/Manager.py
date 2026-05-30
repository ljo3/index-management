from decimal import getcontext, Decimal
from index_management.utilities.utils import fullpath, checkpath
from index_management.utilities.utils import last_day, last_working_day, validate_date
from index_management.utilities.utils import get_datestr
from index_management.validation.models import ValuationConfig, WeightsValidator
import pandas as pd
import numpy as np
from datetime import datetime

class Valuation:

    def __init__(self, current_date, module):
        self.inception_date = validate_date("2020-12-31")
        self.current_date = validate_date(current_date)
        self.last_day = last_day(self.current_date)
        self.last_working_day = last_working_day(self.current_date)
        self.module = module

        # initialize folders
        self.valuation_paths()

        # quarters data - to get most recent quarter
        quarters = pd.read_csv(fullpath("data","quarters.txt"), names=["qtr"],  skiprows=1)
        quarters["qtr"] = quarters["qtr"].apply(lambda x: validate_date(x))

        # get prior_weights
        idx = validate_date(self.current_date) > quarters["qtr"]
        if any(idx):
            previous_quarter = max(quarters.loc[idx, "qtr"])
        else:
            previous_quarter = self.current_date

        self.previous_quarter = previous_quarter
        self.universe = fullpath("data","universe","processed",
                                 get_datestr(previous_quarter)+".csv")
        ValuationConfig(current_date=self.current_date, module=self.module)

    def valuation_paths(self):
        self.folder_path_quarterly = fullpath("data", "valuation", "quarterly", self.module)
        self.folder_path_daily = fullpath("data", "valuation", "daily", self.module)
        checkpath(self.folder_path_quarterly)
        checkpath(self.folder_path_daily)

    def valuation_quarterly(self):
        path_weights = fullpath("data","strategy",self.module,get_datestr(self.current_date)+".csv")
        path_price = fullpath("data", "market", "prices",get_datestr(self.current_date)+".csv")
        ptf_size = 1e9

        # read weight and price files
        weights = pd.read_csv(path_weights)
        WeightsValidator(weights=weights)
        prices = pd.read_csv(path_price)

        # convert prices["Date"] to datetime and get just date
        prices['Date'] = pd.to_datetime(prices['Date'])

        #
        price_qtr_end = prices[prices.Date == self.last_working_day].drop("Date", axis=1).transpose()
        price_qtr_end = price_qtr_end.reset_index()
        price_qtr_end.columns = ["Symbol", "Prices"]

        df_prices_weights = pd.merge(price_qtr_end, weights, left_on="Symbol", right_on="Symbol")
        df_prices_weights["DollarWeight"] = df_prices_weights["Weights"].apply(lambda x: ptf_size*x )
        df_prices_weights["NumShares"] = df_prices_weights["DollarWeight"].values / df_prices_weights["Prices"].values

        df_prices_weights["NumShares"] = np.floor( df_prices_weights["DollarWeight"] / df_prices_weights["Prices"] )
        cash = (ptf_size - sum(df_prices_weights["NumShares"]*df_prices_weights["Prices"]))

        df_cash = pd.DataFrame({"Symbol": "cash", "Prices": 1, "Weights": cash/ptf_size, "DollarWeight": cash, "NumShares": cash }, index=range(1))
        df_asset_table = pd.concat([df_prices_weights, df_cash])

        df_quarterly_allocation = df_asset_table.loc[df_asset_table["Symbol"] != "cash", ["Symbol", "NumShares"]]

        df_quarterly_allocation.to_csv(fullpath(self.folder_path_quarterly,get_datestr(self.current_date)+".csv"), index=False)

        return df_quarterly_allocation
