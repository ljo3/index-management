import unittest
from index_management.universe.Manager import Universe
from index_management.utilities.utils import fullpath, get_datestr
import pandas as pd

class TestUniverse(unittest.TestCase):

    def setUp(self):
        self.current_date = "20250331"
        self.unv = Universe(self.current_date)
        self.unv_path = fullpath(self.unv.path_universe("processed"),get_datestr(self.current_date)+".csv")
        self.df_unv = pd.read_csv(self.unv_path)

    def test_constructor(self):
        self.assertIsNotNone(self.unv)

    def test_na_in_universe(self):
        self.assertEqual(self.df_unv.isna().sum().sum(), 0)
