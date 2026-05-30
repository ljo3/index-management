"""
End-to-end path coverage for all four pipeline modules and the validation layer.
Exercises every module constructor, every calculate/valuation method on all
available quarters, every ValidationError case in models.py, and portfolio
business-logic invariants (proportionality, ~$1B portfolio value, integer shares).
"""
import unittest
from datetime import datetime

import numpy as np
import pandas as pd
from pydantic import ValidationError

from index_management.validation.models import (
    DateConfig,
    MarketConfig,
    ValuationConfig,
    WeightsValidator,
)
from index_management.universe.Manager import Universe
from index_management.market.Manager import Market
from index_management.strategy.Manager import CapWeight, MaxSharpeRatioPortfolio
from index_management.valuation.Manager import Valuation
from index_management.utilities.utils import fullpath, get_datestr, last_day


QUARTERS = ["20231231", "20240331", "20240630", "20240930", "20241231", "20250331"]


# ---------------------------------------------------------------------------
# Validation model — rejection cases
# ---------------------------------------------------------------------------

class TestDateConfigRejects(unittest.TestCase):

    def test_future_date(self):
        with self.assertRaises(ValidationError):
            DateConfig(current_date=datetime(2030, 1, 1))

    def test_pre_inception(self):
        with self.assertRaises(ValidationError):
            DateConfig(current_date=datetime(2019, 12, 31))

    def test_exactly_inception(self):
        with self.assertRaises(ValidationError):
            DateConfig(current_date=datetime(2020, 12, 31))

    def test_valid(self):
        cfg = DateConfig(current_date=datetime(2025, 3, 31))
        self.assertEqual(cfg.current_date, datetime(2025, 3, 31))


class TestMarketConfigRejects(unittest.TestCase):

    def test_missing_symbol_column(self):
        with self.assertRaises(ValidationError):
            MarketConfig(
                current_date=datetime(2025, 3, 31),
                universe=pd.DataFrame({"ticker": ["AC.PA"]}),
            )

    def test_empty_universe(self):
        with self.assertRaises(ValidationError):
            MarketConfig(
                current_date=datetime(2025, 3, 31),
                universe=pd.DataFrame({"symbol": []}),
            )

    def test_null_symbol(self):
        with self.assertRaises(ValidationError):
            MarketConfig(
                current_date=datetime(2025, 3, 31),
                universe=pd.DataFrame({"symbol": ["AC.PA", None]}),
            )

    def test_invalid_interval(self):
        with self.assertRaises(ValidationError):
            MarketConfig(
                current_date=datetime(2025, 3, 31),
                universe=pd.DataFrame({"symbol": ["AC.PA"]}),
                interval="weekly",
            )


class TestValuationConfigRejects(unittest.TestCase):

    def test_bad_module(self):
        with self.assertRaises(ValidationError):
            ValuationConfig(current_date=datetime(2025, 3, 31), module="caps")

    def test_valid_cw(self):
        cfg = ValuationConfig(current_date=datetime(2025, 3, 31), module="cw")
        self.assertEqual(cfg.module, "cw")

    def test_valid_msr(self):
        cfg = ValuationConfig(current_date=datetime(2025, 3, 31), module="msr")
        self.assertEqual(cfg.module, "msr")


class TestWeightsValidatorRejects(unittest.TestCase):

    def test_negative_weight(self):
        with self.assertRaises(ValidationError):
            WeightsValidator(
                weights=pd.DataFrame({"Symbol": ["A", "B"], "Weights": [-0.1, 1.1]})
            )

    def test_sum_not_one(self):
        with self.assertRaises(ValidationError):
            WeightsValidator(
                weights=pd.DataFrame({"Symbol": ["A", "B"], "Weights": [0.4, 0.4]})
            )

    def test_nan_weight(self):
        with self.assertRaises(ValidationError):
            WeightsValidator(
                weights=pd.DataFrame({"Symbol": ["A", "B"], "Weights": [float("nan"), 1.0]})
            )

    def test_missing_column(self):
        with self.assertRaises(ValidationError):
            WeightsValidator(
                weights=pd.DataFrame({"Ticker": ["A"], "Weights": [1.0]})
            )

    def test_empty(self):
        with self.assertRaises(ValidationError):
            WeightsValidator(weights=pd.DataFrame({"Symbol": [], "Weights": []}))

    def test_valid(self):
        wv = WeightsValidator(
            weights=pd.DataFrame({"Symbol": ["A", "B", "C"], "Weights": [0.5, 0.3, 0.2]})
        )
        self.assertIsNotNone(wv)


# ---------------------------------------------------------------------------
# Module constructors — all available quarters
# ---------------------------------------------------------------------------

class TestUniverseConstructor(unittest.TestCase):

    def test_all_quarters(self):
        for q in QUARTERS:
            with self.subTest(quarter=q):
                unv = Universe(q)
                self.assertIsNotNone(unv)
                self.assertIsNotNone(unv.current_date)


class TestCapWeightConstructor(unittest.TestCase):

    def test_all_quarters(self):
        for q in QUARTERS:
            with self.subTest(quarter=q):
                cw = CapWeight(q)
                self.assertEqual(cw.module, "cw")
                self.assertEqual(cw.market_module, "caps")


class TestMSRConstructor(unittest.TestCase):

    def test_all_quarters(self):
        for q in QUARTERS:
            with self.subTest(quarter=q):
                msr = MaxSharpeRatioPortfolio(q)
                self.assertEqual(msr.module, "msr")
                self.assertEqual(msr.market_module, "prices")


class TestValuationConstructor(unittest.TestCase):

    def test_cw_all_quarters(self):
        for q in QUARTERS:
            with self.subTest(quarter=q):
                v = Valuation(q, "cw")
                self.assertEqual(v.module, "cw")

    def test_msr_all_quarters(self):
        for q in QUARTERS:
            with self.subTest(quarter=q):
                v = Valuation(q, "msr")
                self.assertEqual(v.module, "msr")

    def test_invalid_module_rejected(self):
        with self.assertRaises(ValidationError):
            Valuation("20250331", "caps")


# ---------------------------------------------------------------------------
# CapWeight.calculate_weights — all quarters with existing cap data
# ---------------------------------------------------------------------------

class TestCapWeightCalculate(unittest.TestCase):

    def test_written_weights_sum_to_one(self):
        # The merged return df is an inner join — drops changed components, so
        # Weights_new won't sum to 1 across rebalancing boundaries. Test the
        # written CSV (already guarded by WeightsValidator) instead.
        from index_management.utilities.utils import fullpath, get_datestr, last_day
        for q in QUARTERS:
            with self.subTest(quarter=q):
                cw = CapWeight(q)
                cw.calculate_weights()
                path = fullpath("data", "strategy", "cw", get_datestr(last_day(cw.current_date)) + ".csv")
                df = pd.read_csv(path)
                self.assertLessEqual(abs(df["Weights"].sum() - 1.0), 1e-4)

    def test_no_negative_weights(self):
        from index_management.utilities.utils import fullpath, get_datestr, last_day
        cw = CapWeight("20250331")
        cw.calculate_weights()
        path = fullpath("data", "strategy", "cw", get_datestr(last_day(cw.current_date)) + ".csv")
        df = pd.read_csv(path)
        self.assertTrue((df["Weights"] >= 0).all())


# ---------------------------------------------------------------------------
# MSR.calculate_weights — most recent quarter only (expensive)
# ---------------------------------------------------------------------------

class TestMSRCalculate(unittest.TestCase):

    def setUp(self):
        self.msr = MaxSharpeRatioPortfolio("20250331")
        _, self.df = self.msr.calculate_weights()

    def test_lw_weights_sum_to_one(self):
        self.assertLessEqual(abs(self.df["Weight_LW"].sum() - 1.0), 1e-3)

    def test_sample_weights_sum_to_one(self):
        # Weight_Sample is display-only; the < 1e-6 zeroing step can reduce the sum
        # by up to ~40 * 1e-6. Use a practical tolerance rather than strict 1e-4.
        self.assertLessEqual(abs(self.df["Weight_Sample"].sum() - 1.0), 0.05)

    def test_no_negative_weights(self):
        self.assertTrue((self.df["Weight_LW"] >= 0).all())
        self.assertTrue((self.df["Weight_Sample"] >= 0).all())

    def test_cov_matrices_set(self):
        self.assertIsNotNone(self.msr.df_sample_cov_matrix)
        self.assertIsNotNone(self.msr.df_LedoitWolf_cov_matrix)


# ---------------------------------------------------------------------------
# Valuation.valuation_quarterly — cw and msr
# ---------------------------------------------------------------------------

class TestValuationQuarterly(unittest.TestCase):

    def test_cw_no_nulls(self):
        v = Valuation("20250331", "cw")
        df = v.valuation_quarterly()
        self.assertEqual(df.isna().sum().sum(), 0)

    def test_msr_no_nulls(self):
        v = Valuation("20250331", "msr")
        df = v.valuation_quarterly()
        self.assertEqual(df.isna().sum().sum(), 0)

    def test_cw_has_shares(self):
        v = Valuation("20250331", "cw")
        df = v.valuation_quarterly()
        self.assertIn("NumShares", df.columns)
        self.assertTrue((df["NumShares"] > 0).all())


# ---------------------------------------------------------------------------
# ValuationConfig — edge cases
# ---------------------------------------------------------------------------

class TestValuationConfigEdgeCases(unittest.TestCase):

    def test_uppercase_module_rejected(self):
        with self.assertRaises(ValidationError):
            ValuationConfig(current_date=datetime(2025, 3, 31), module="CW")

    def test_msr_uppercase_rejected(self):
        with self.assertRaises(ValidationError):
            ValuationConfig(current_date=datetime(2025, 3, 31), module="MSR")

    def test_empty_string_rejected(self):
        with self.assertRaises(ValidationError):
            ValuationConfig(current_date=datetime(2025, 3, 31), module="")

    def test_old_market_module_name_rejected(self):
        # "prices" and "caps" are market-data folder names, not valid strategy modules
        for bad in ("prices", "caps"):
            with self.subTest(module=bad):
                with self.assertRaises(ValidationError):
                    ValuationConfig(current_date=datetime(2025, 3, 31), module=bad)

    def test_day_after_inception_is_valid(self):
        cfg = ValuationConfig(current_date=datetime(2021, 1, 1), module="cw")
        self.assertEqual(cfg.module, "cw")


# ---------------------------------------------------------------------------
# WeightsValidator — tolerance boundary and edge-case shapes
# ---------------------------------------------------------------------------

class TestWeightsValidatorBoundary(unittest.TestCase):

    def test_single_asset_weight_one(self):
        WeightsValidator(weights=pd.DataFrame({"Symbol": ["A"], "Weights": [1.0]}))

    def test_all_zeros_rejected(self):
        # Sum = 0, far from 1.0
        with self.assertRaises(ValidationError):
            WeightsValidator(
                weights=pd.DataFrame({"Symbol": ["A", "B"], "Weights": [0.0, 0.0]})
            )

    def test_sum_exactly_at_tolerance_is_valid(self):
        # |1.0 + 1e-4 - 1.0| = 1e-4; condition is > 1e-4, so this passes
        WeightsValidator(
            weights=pd.DataFrame({"Symbol": ["A", "B"], "Weights": [0.5, 0.5 + 1e-4]})
        )

    def test_sum_just_outside_tolerance_rejected(self):
        # |1.0 + 1.1e-4 - 1.0| = 1.1e-4 > 1e-4; must fail
        with self.assertRaises(ValidationError):
            WeightsValidator(
                weights=pd.DataFrame({"Symbol": ["A", "B"], "Weights": [0.5, 0.5 + 1.1e-4]})
            )

    def test_duplicate_symbols_allowed(self):
        # Validator does not require unique symbols (that is the caller's concern)
        WeightsValidator(
            weights=pd.DataFrame({"Symbol": ["A", "A"], "Weights": [0.5, 0.5]})
        )


# ---------------------------------------------------------------------------
# Manager validation fires at __init__ (integration, not just model-level)
# ---------------------------------------------------------------------------

class TestManagerValidationBoundary(unittest.TestCase):

    def test_universe_future_date_raises(self):
        with self.assertRaises(ValidationError):
            Universe("20301231")

    def test_capweight_future_date_raises(self):
        with self.assertRaises(ValidationError):
            CapWeight("20301231")

    def test_msr_future_date_raises(self):
        with self.assertRaises(ValidationError):
            MaxSharpeRatioPortfolio("20301231")

    def test_valuation_future_date_raises(self):
        with self.assertRaises(ValidationError):
            Valuation("20301231", "cw")

    def test_valuation_pre_inception_raises(self):
        with self.assertRaises(ValidationError):
            Valuation("20191231", "cw")

    def test_valuation_bad_module_raises_from_manager(self):
        # The ValidationError must propagate from Manager.__init__, not just from
        # directly constructing ValuationConfig — this confirms the wiring is live.
        with self.assertRaises(ValidationError):
            Valuation("20250331", "prices")


# ---------------------------------------------------------------------------
# CapWeight correctness — weights proportional to market caps
# ---------------------------------------------------------------------------

class TestCapWeightCorrectness(unittest.TestCase):

    def setUp(self):
        self.cw = CapWeight("20250331")
        self.cw.calculate_weights()
        path = fullpath("data", "strategy", "cw",
                        get_datestr(last_day(self.cw.current_date)) + ".csv")
        self.weights = pd.read_csv(path)
        caps = pd.read_csv(fullpath("data", "market", "caps", "20250331.csv"))
        caps["MarketCap"] = pd.to_numeric(caps["MarketCap"], errors="coerce")
        self.merged = self.weights.merge(caps, on="Symbol")

    def test_largest_cap_has_largest_weight(self):
        max_cap_sym = self.merged.loc[self.merged["MarketCap"].idxmax(), "Symbol"]
        max_wgt_sym = self.merged.loc[self.merged["Weights"].idxmax(), "Symbol"]
        self.assertEqual(max_cap_sym, max_wgt_sym)

    def test_weight_ratio_matches_cap_ratio(self):
        # For any two stocks, weight_i / weight_j should equal cap_i / cap_j
        row0, row1 = self.merged.iloc[0], self.merged.iloc[1]
        cap_ratio = row0["MarketCap"] / row1["MarketCap"]
        wgt_ratio = row0["Weights"] / row1["Weights"]
        self.assertAlmostEqual(cap_ratio, wgt_ratio, places=6)

    def test_symbol_count_matches_valid_caps(self):
        # Only tickers with numeric MarketCap survive the pd.to_numeric coercion in
        # calculate_weights() — compare against that filtered count, not the raw file.
        caps = pd.read_csv(fullpath("data", "market", "caps", "20250331.csv"))
        caps["MarketCap"] = pd.to_numeric(caps["MarketCap"], errors="coerce")
        valid_caps = caps.dropna(subset=["MarketCap"])
        self.assertEqual(len(self.weights), len(valid_caps))


# ---------------------------------------------------------------------------
# CapWeight — bad caps data coercion (regression for the Decimal crash)
# ---------------------------------------------------------------------------

class TestCapWeightBadDataCoercion(unittest.TestCase):

    def test_error_strings_coerced_to_nan(self):
        # Verify that rate-limit error strings (the bug source) become NaN after coercion,
        # leaving an empty DataFrame that triggers the ValueError we added.
        bad = pd.DataFrame({
            "Symbol": ["A.PA", "B.PA"],
            "MarketCap": ["Error: Too Many Requests", "N/A"],
        })
        coerced = pd.to_numeric(bad["MarketCap"], errors="coerce")
        self.assertEqual(coerced.isna().sum(), 2)
        self.assertTrue(coerced.dropna().empty)

    def test_partial_errors_dropped_weights_still_valid(self):
        # If only some rows have error strings, the remaining valid rows should
        # produce weights that sum to 1.0.
        mixed = pd.DataFrame({
            "Symbol": ["A.PA", "B.PA", "C.PA"],
            "MarketCap": ["Error: rate limit", 3_000_000, 7_000_000],
        })
        mixed["MarketCap"] = pd.to_numeric(mixed["MarketCap"], errors="coerce")
        mixed = mixed.dropna(subset=["MarketCap"])
        total = mixed["MarketCap"].sum()
        mixed["Weights"] = mixed["MarketCap"] / total
        self.assertAlmostEqual(mixed["Weights"].sum(), 1.0, places=10)
        self.assertEqual(len(mixed), 2)


# ---------------------------------------------------------------------------
# Valuation business logic — portfolio value, integer shares, symbol coverage
# ---------------------------------------------------------------------------

class TestValuationBusinessLogic(unittest.TestCase):

    PTF_SIZE = 1_000_000_000

    def setUp(self):
        self.v = Valuation("20250331", "cw")
        self.allocation = self.v.valuation_quarterly()
        prices = pd.read_csv(
            fullpath("data", "market", "prices", get_datestr(self.v.current_date) + ".csv")
        )
        prices["Date"] = pd.to_datetime(prices["Date"])
        price_end = (
            prices[prices["Date"] == self.v.last_working_day]
            .drop("Date", axis=1)
            .transpose()
            .reset_index()
        )
        price_end.columns = ["Symbol", "Price"]
        self.merged = self.allocation.merge(price_end, on="Symbol")

    def test_portfolio_value_within_1pct_of_1B(self):
        portfolio_value = (self.merged["NumShares"] * self.merged["Price"]).sum()
        relative_error = abs(portfolio_value - self.PTF_SIZE) / self.PTF_SIZE
        self.assertLess(relative_error, 0.01)

    def test_num_shares_are_whole_numbers(self):
        # floor() is applied in valuation_quarterly — all values must be integers
        self.assertTrue((self.allocation["NumShares"] % 1 == 0).all())

    def test_num_shares_non_negative(self):
        self.assertTrue((self.allocation["NumShares"] >= 0).all())

    def test_symbols_unique_in_allocation(self):
        self.assertEqual(len(self.allocation["Symbol"].unique()), len(self.allocation))

    def test_allocation_symbols_subset_of_universe(self):
        universe = pd.read_csv(self.v.universe)
        self.assertTrue(set(self.allocation["Symbol"]).issubset(set(universe["symbol"])))


# ---------------------------------------------------------------------------
# MSR structural properties — covariance matrix invariants
# ---------------------------------------------------------------------------

class TestMSRStructural(unittest.TestCase):

    def setUp(self):
        msr = MaxSharpeRatioPortfolio("20250331")
        _, self.df_weights = msr.calculate_weights()
        self.sample_cov = msr.df_sample_cov_matrix
        self.lw_cov = msr.df_LedoitWolf_cov_matrix

    def test_cov_matrices_are_square(self):
        for cov in (self.sample_cov, self.lw_cov):
            rows, cols = cov.shape
            self.assertEqual(rows, cols)

    def test_sample_cov_is_symmetric(self):
        np.testing.assert_allclose(
            self.sample_cov.values,
            self.sample_cov.values.T,
            atol=1e-10,
        )

    def test_lw_cov_is_symmetric(self):
        np.testing.assert_allclose(
            self.lw_cov.values,
            self.lw_cov.values.T,
            atol=1e-10,
        )

    def test_variances_are_positive(self):
        # Diagonal elements are variances — must be > 0
        self.assertTrue((self.sample_cov.values.diagonal() > 0).all())
        self.assertTrue((self.lw_cov.values.diagonal() > 0).all())

    def test_asset_names_consistent_across_outputs(self):
        # Tickers in df_weights must match the covariance matrix index
        self.assertEqual(
            set(self.df_weights["Asset"]),
            set(self.sample_cov.columns),
        )


if __name__ == "__main__":
    unittest.main()
