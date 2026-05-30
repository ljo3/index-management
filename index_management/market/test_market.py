import unittest
from index_management.utilities.utils import fullpath
import pandas as pd

class TestMarket(unittest.TestCase):

    def setUp(self):
        self.market_path = fullpath("data", "market", "caps","20250331.csv")

    def test_na_in_caps(self):
        df_market_caps = pd.read_csv(self.market_path)
        count_na = df_market_caps.isna().sum().sum()
        self.assertEqual(count_na, 0)
