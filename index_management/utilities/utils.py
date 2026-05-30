import os
import pandas as pd
import re
from datetime import datetime
from datetime import date

def fullpath(*args):
    return os.path.join( *args )

def checkpath(folder_path):
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

def validate_date(input_date: str|datetime):
    if isinstance(input_date, int):
        input_date = str(input_date)

    if isinstance(input_date, str):
        input_date = "".join(re.findall(r"\d+", input_date))
        try:
            formatted_date = datetime.strptime(input_date, "%Y%m%d")
        except ValueError:
            print("Date format should be YYYYMMDD")

    if isinstance(input_date, (datetime,date)):
        formatted_date = input_date

    return formatted_date

def get_datetime(input_date: str|datetime):
    formatted_date = validate_date(input_date)
    return formatted_date

def get_datestr(input_date: str|datetime):
    formatted_date = validate_date(input_date).strftime("%Y%m%d")
    return formatted_date


def last_day(input_date):
    formatted_date = validate_date(input_date)
    last_day_of_month = formatted_date + pd.offsets.MonthEnd(0)
    return last_day_of_month

def last_working_day(input_date):
    last_day_of_month = last_day(input_date)

    if last_day_of_month.weekday() in [5, 6]:  # 5 = Saturday, 6 = Sunday
        last_working_day = last_day_of_month - pd.offsets.Week(weekday=4)  # 4 = Friday
    else:
        last_working_day = last_day_of_month

    return last_working_day
