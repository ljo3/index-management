import unittest
from index_management.utilities.utils import fullpath
from index_management.valuation.Manager import Valuation

class TestMarket(unittest.TestCase):

    def setUp(self):
        pass

    def test_na_in_caps(self):
        value = Valuation(20250331, "cw")
        df_weights = value.valuation_quarterly()
        self.assertEqual(df_weights.isna().sum().sum(), 0.0)

    def test_na_in_msr(self):
        value = Valuation(20250331, "msr")
        df_weights = value.valuation_quarterly()
        self.assertEqual(df_weights.isna().sum().sum(), 0.0)
