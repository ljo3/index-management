import unittest
from index_management.utilities.utils import fullpath, get_datestr, get_datetime, last_working_day, last_day, validate_date
from datetime import datetime
import pandas as pd

class TestUtilities(unittest.TestCase):

    def test_datetime(self):
        self.assertEqual(get_datetime( get_datestr(20231231) ), datetime(2023,12,31))

    def test_datestr(self):
        self.assertEqual(get_datestr(get_datetime( get_datestr(20231231) )), "20231231")

    def test_last_working_day(self):
        self.assertEqual(last_working_day(20231231), datetime(2023,12,29))

    def test_last_day(self):
        self.assertEqual(last_day(20230101), datetime(2023,1,31))
