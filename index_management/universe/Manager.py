import os
import pandas as pd
import requests
from index_management.utilities.utils import fullpath, checkpath
from index_management.utilities.utils import last_day, last_working_day, validate_date
from index_management.utilities.utils import get_datestr

class Universe:

    def __init__(self, current_date):
        self.inception_date = validate_date("2020-12-31")
        self.current_date = validate_date(current_date)
        self.last_day = last_day(self.current_date)
        self.last_working_day = last_working_day(self.current_date)

    def path_universe(self, module):
        # module could be raw or processed
        folder_path = fullpath("data", "universe", module)
        checkpath(folder_path)
        return folder_path

    def get_raw_universe(self):

        # universe path
        path_universe = self.path_universe("raw")
        path_universe = fullpath(path_universe, get_datestr(self.last_day)+".csv")
        self.universe = pd.read_csv(path_universe, skiprows=[0,1])

        # get yfinance codes from isin_codes
        isin_codes = list( self.universe.iloc[:, 0] )

        def get_symbol_for_isin(isin):
            url = 'https://query1.finance.yahoo.com/v1/finance/search'
            headers = { 'User-Agent': 'lj'}
            params = dict(q=isin)
            resp = requests.get(url=url, headers=headers, params=params)
            data = resp.json()
            if 'quotes' in data and len(data['quotes']) > 0:
                return data['quotes'][0]['symbol']
            else:
                return None

        symbol_list = list()
        for i in isin_codes:
            isin = i
            symbol = get_symbol_for_isin(isin)
            symbol_list.append(symbol)

        self.universe['symbol'] = symbol_list

        return self.universe
