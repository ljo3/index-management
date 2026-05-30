import unittest
from index_management.strategy.Manager import CapWeight
from index_management.strategy.Manager import MaxSharpeRatioPortfolio

class TestStrategy(unittest.TestCase):

    def setUp(self):
        pass

    def test_cap_weight(self):
        cw = CapWeight(20250331)
        cw.path_strategy("caps")
        [old, df_wgts] = cw.calculate_weights()
        self.assertLessEqual(abs(df_wgts["Weights_new"].sum() - 1.0), 0.1)

    def test_msr(self):
        msr = MaxSharpeRatioPortfolio(20250331)
        [prior, df_weights] = msr.calculate_weights()
        self.assertLessEqual(abs(df_weights["Weight_LW"].sum() - 1.0), 0.1)
