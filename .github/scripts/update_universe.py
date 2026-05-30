"""
Fetches the current CAC 40 composition from bnains.org, saves the raw file,
resolves ISINs to Yahoo Finance symbols, and updates quarters.txt.

Run by GitHub Actions on the last few days of each quarter month so the job
cannot miss the quarter-end. The script is idempotent: if this quarter has
already been processed it exits early.

When the quarter-end falls on a weekend the universe is still saved under the
quarter-end date (e.g. 20250331), but last_working_day() is used for any
price-date lookups so downstream modules get Friday data automatically.
"""
import os
import sys
import requests
import pandas as pd
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from index_management.universe.Manager import Universe
from index_management.utilities.utils import fullpath, checkpath, get_datestr, last_day

SOURCE_URL = 'https://www.bnains.org/archives/histocac/compocac.php'
QUARTERS_FILE = fullpath('data', 'quarters.txt')


def already_processed(date_str: str) -> bool:
    """Return True if this quarter has already been saved."""
    with open(QUARTERS_FILE) as f:
        return date_str in f.read().splitlines()


def fetch_cac40() -> pd.DataFrame:
    resp = requests.get(SOURCE_URL, headers={'User-Agent': 'Mozilla/5.0'}, timeout=30)
    resp.raise_for_status()
    tables = pd.read_html(resp.text, header=0)
    for t in tables:
        if any('ISIN' in str(c) for c in t.columns):
            return t
    raise ValueError("CAC 40 constituent table not found on page")


def save_raw(df: pd.DataFrame, date_str: str) -> None:
    path = fullpath('data', 'universe', 'raw', date_str + '.csv')
    checkpath(os.path.dirname(path))
    with open(path, 'w', encoding='utf-8') as f:
        f.write(f'source: {SOURCE_URL}\n')
        f.write(f'Liste des 40 valeurs du CAC40 au {datetime.today().strftime("%d/%m/%Y")},,\n')
        df.to_csv(f, index=False)
    print(f'Saved raw universe: {path}')


def save_processed(df: pd.DataFrame, date_str: str) -> None:
    path = fullpath('data', 'universe', 'processed', date_str + '.csv')
    checkpath(os.path.dirname(path))
    df.to_csv(path, index=False)
    print(f'Saved processed universe: {path}')


def update_quarters(date_str: str) -> None:
    with open(QUARTERS_FILE) as f:
        lines = f.read().splitlines()
    lines.append(date_str)
    lines.sort()
    with open(QUARTERS_FILE, 'w') as f:
        f.write('\n'.join(lines) + '\n')
    print(f'Added {date_str} to quarters.txt')


def main():
    today = datetime.today()

    # Quarter-end is always the last calendar day of the month.
    # Using last_day() means the file is always named after the true quarter-end
    # (e.g. 20250331) even when the job fires a day early or the date is a weekend.
    date_str = get_datestr(last_day(today))

    if already_processed(date_str):
        print(f'Quarter {date_str} already processed — nothing to do.')
        return

    print(f'Quarter-end date: {date_str}')
    print(f'Fetching CAC 40 composition from {SOURCE_URL} ...')

    df_raw = fetch_cac40()
    print(f'Found {len(df_raw)} constituents')

    save_raw(df_raw, date_str)

    # Resolve ISINs to Yahoo Finance symbols.
    # Universe internally uses last_working_day() so weekend quarter-ends
    # fall back to the preceding Friday automatically.
    unv = Universe(date_str)
    df_processed = unv.get_raw_universe()
    save_processed(df_processed, date_str)

    update_quarters(date_str)


if __name__ == '__main__':
    main()
