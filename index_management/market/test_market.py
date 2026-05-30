import unittest
from index_management.utilities.utils import fullpath
import pandas as pd

class TestMarket(unittest.TestCase):

    def setUp(self):
        self.market_path = fullpath("data", "market", "caps","20250331.csv")

    def test_na_in_caps(self):
        df_market_caps = pd.read_csv(self.market_path)
        count_na = df_market_caps["MarketCap"].isna().sum()
        # A small number of tickers may become unavailable (delisted, no data on yfinance).
        # calculate_weights() drops them; the important thing is that most tickers have data.
        self.assertLessEqual(count_na, 3)

    def test_caps_majority_numeric(self):
        df_market_caps = pd.read_csv(self.market_path)
        numeric_count = pd.to_numeric(df_market_caps["MarketCap"], errors="coerce").notna().sum()
        # At least 90% of tickers must have valid numeric market caps
        self.assertGreaterEqual(numeric_count, len(df_market_caps) * 0.9)
