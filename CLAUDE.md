# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment setup

Uses [uv](https://github.com/astral-sh/uv) with a `.venv` at repo root. **PYTHONPATH must be set to the repo root** — without it, `from index_management.X import Y` fails.

```bash
uv venv && uv pip install -r requirements.txt
source .venv/bin/activate
export PYTHONPATH=$(pwd)
```

## Commands

```bash
# Run all tests
pytest

# Run a single test file
pytest index_management/market/test_market.py

# Launch the Streamlit portfolio visualization app
streamlit run app_portfolio_visualize.py   # → http://localhost:8501

# Run daily valuation (also triggered by GitHub Actions on push to main)
python .github/scripts/value_daily.py

# Run quarterly universe update manually (normally run by GitHub Actions)
python .github/scripts/update_universe.py
```

## Layout

```
repo root/
├── driver.ipynb                        # end-to-end demo (start here)
├── app_portfolio_visualize.py          # Streamlit app (MSR portfolio)
├── data/                               # all CSV inputs/outputs (not in package)
│   ├── quarters.txt                    # quarter-end dates driving rebalancing
│   ├── universe/{raw,processed}/
│   ├── market/{prices,caps}/
│   ├── strategy/{caps,msr}/
│   └── valuation/{quarterly,daily}/
├── .github/
│   ├── scripts/
│   │   ├── value_daily.py              # CI script: daily portfolio valuation
│   │   └── update_universe.py          # CI script: quarterly universe fetch + ISIN resolution
│   └── workflows/
│       ├── valuation.yml               # triggers on push to main
│       └── update_universe.yml         # triggers near each quarter-end
└── index_management/                   # the library package
    ├── universe/Manager.py
    ├── market/Manager.py
    ├── strategy/Manager.py
    ├── valuation/Manager.py
    ├── utilities/utils.py
    └── drivers/                        # detailed per-module driver notebooks
```

## Architecture

The project tracks the **CAC 40** index and implements a quarterly rebalancing pipeline. Data flows left to right through four modules, each with a `Manager.py` containing a class initialized with a `current_date` (YYYYMMDD string or datetime):

```
Universe → Market → Strategy → Valuation
```

**`universe/Manager.py` — `Universe`**
Resolves ISIN codes from a raw CSV (`data/universe/raw/`) to Yahoo Finance ticker symbols via the Yahoo Finance search API, writing results to `data/universe/processed/`. The raw CSV is fetched from `bnains.org` by `update_universe.py`.

**`market/Manager.py` — `Market`**
Fetches price history (`get_prices`, `get_daily_prices`) and market caps (`get_caps`) from `yfinance` for the processed universe. Saves CSVs to `data/market/prices/` and `data/market/caps/`. Reads the most recent processed universe by looking up `data/quarters.txt`.

**`strategy/Manager.py` — `BaseStrategy`, `CapWeight`, `MaxSharpeRatioPortfolio`**
`BaseStrategy` (ABC) defines `calculate_weights()` and `prepare_strategy()`, which loads the relevant market data CSV and the prior quarter's weights. Two concrete implementations:
- `CapWeight` — proportional market-cap weighting, writes to `data/strategy/caps/`
- `MaxSharpeRatioPortfolio` — mean-variance optimization using both sample and Ledoit-Wolf shrunk covariance, writes to `data/strategy/msr/`

**`valuation/Manager.py` — `Valuation`**
Takes a strategy module name (`"cw"` or `"msr"`), converts weights + end-of-quarter prices into share counts for a $1B notional portfolio, saves to `data/valuation/quarterly/`. The CI script `value_daily.py` uses the quarterly allocations plus live prices to compute and write daily portfolio values to `data/valuation/daily/cw/`.

**`utilities/utils.py`**
Date helpers (`validate_date`, `get_datestr`, `last_day`, `last_working_day`) and path helpers (`fullpath`, `checkpath`). All modules import from here.

**`app_portfolio_visualize.py`**
Streamlit app that runs `MaxSharpeRatioPortfolio.calculate_weights()` for a user-selected quarter and displays weight bar charts and covariance matrix heatmaps (sample vs. Ledoit-Wolf).

## Data conventions

- Dates in filenames: `YYYYMMDD` (e.g., `20250331.csv`)
- `data/quarters.txt` lists quarter-end dates — every Manager reads this to find the most recent prior quarter for loading universe and prior weights
- All file paths are constructed with `utilities.utils.fullpath()` (wraps `os.path.join`); paths are relative to CWD (repo root)
- `CapWeight` writes strategy files using `last_day` (last calendar day of month) as the filename; pass quarter-end dates as `current_date` to keep filenames consistent with what `Valuation` expects

## CI/CD

Two GitHub Actions workflows:

- **`valuation.yml`** — triggers on push to `main`. Runs `.github/scripts/value_daily.py` (cap-weighted daily valuation) and auto-commits the output CSVs back to the repo. Scheduled cron trigger is currently commented out.
- **`update_universe.yml`** — triggers on the last few days of each quarter month (March, June, September, December) and can be run manually via `workflow_dispatch`. Runs `.github/scripts/update_universe.py`, which fetches the current CAC 40 composition, resolves ISINs to Yahoo Finance symbols, and appends the new quarter-end date to `quarters.txt`. The script is idempotent — it exits early if the quarter has already been processed.
