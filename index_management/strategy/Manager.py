from abc import ABC, abstractmethod
from index_management.utilities.utils import fullpath, checkpath
from index_management.utilities.utils import last_day, last_working_day, validate_date
from index_management.utilities.utils import get_datestr, get_datetime
from index_management.validation.models import DateConfig, WeightsValidator
import pandas as pd
import numpy as np
from decimal import getcontext, Decimal
from scipy.optimize import minimize
from sklearn.covariance import LedoitWolf
from sklearn.decomposition import PCA


getcontext().prec = 16

class BaseStrategy(ABC):
    """ Setting base strategy with expected signature """

    @abstractmethod
    def calculate_weights(self):
        pass

    def path_strategy(self,module):
        folder_path = fullpath("data", "strategy", module)
        checkpath(folder_path)
        return fullpath(folder_path)

    def path_market(self,module):
        folder_path = fullpath("data", "market", module)
        checkpath(folder_path)
        return fullpath(folder_path)

    def prepare_strategy(self):

        # get market data
        path_data_market = fullpath( self.path_market(self.market_module),
                                     get_datestr(self.current_date)+".csv" )
        data_market = pd.read_csv(path_data_market)

        # quarters data - to compare weights with previous quarters
        quarters = pd.read_csv(fullpath("data","quarters.txt"), names=["qtr"],  skiprows=1)
        quarters["qtr"] = quarters["qtr"].apply(lambda x: validate_date(x))

        # get prior_weights
        idx = validate_date(self.current_date) > quarters["qtr"]
        if any(idx):
            previous_quarter = max(quarters.loc[idx, "qtr"])
            prior_weights = pd.read_csv(fullpath( self.path_strategy("cw"),
                                                  get_datestr(previous_quarter)+".csv" ))
        else:
            prior_weights = None

        return data_market, prior_weights

class CapWeight(BaseStrategy):

    """ Implements cap weighted indices """

    def __init__(self, current_date):
        self.inception_date = validate_date("2020-12-31")
        self.current_date = validate_date(current_date)
        self.last_day = last_day(self.current_date)
        self.last_working_day = last_working_day(self.current_date)
        self.module = "cw"
        self.market_module = "caps"
        DateConfig(current_date=self.current_date)

    def calculate_weights(self):

        # get current market data and prior weights
        [data_market, prior_weights] = self.prepare_strategy()

        data_market["MarketCap"] = pd.to_numeric(data_market["MarketCap"], errors="coerce")
        data_market = data_market.dropna(subset=["MarketCap"])
        if data_market.empty:
            raise ValueError(f"No valid MarketCap data for {get_datestr(self.current_date)} — file may contain rate-limit errors")

        total_market_cap = Decimal(str(data_market["MarketCap"].sum()))
        data_market["Weights"] = data_market["MarketCap"].apply(lambda x: float(Decimal(str(x)) / total_market_cap))


        path_new_weights = fullpath(self.path_strategy(self.module),
                                    get_datestr(self.last_day)+".csv")
        new_weights = data_market.loc[:,["Symbol","Weights"]]
        WeightsValidator(weights=new_weights)
        new_weights.to_csv(path_new_weights, index=False)

        if prior_weights is not None:
            df_weights = pd.merge(prior_weights, new_weights, on="Symbol", suffixes=('_old', '_new'))
        else:
            df_weights = new_weights.rename(columns={"Weights": "Weights_new"})

        return prior_weights, df_weights

class MaxSharpeRatioPortfolio(BaseStrategy):

    """ Implements max Sharpe ratio portfolio via mean-variance optimization """

    def __init__(self, current_date):
        self.inception_date = validate_date("2020-12-31")
        self.current_date = validate_date(current_date)
        self.last_day = last_day(self.current_date)
        self.last_working_day = last_working_day(self.current_date)
        self.module = "msr"
        self.market_module = "prices"
        self.risk_free_rate = 0.035
        DateConfig(current_date=self.current_date)


    def calculate_weights(self):

        # get current market data and prior weights
        [data_market, prior_weights] = self.prepare_strategy()

        # Cast Date to datetime format
        data_market["Date"] = pd.to_datetime(data_market["Date"])

        # build a DF that has all dates to ffill and get end of month values
        start_date,end_date = data_market.iloc[[0,-1]]['Date'].values

        all_dates = pd.date_range(start=start_date, end=end_date)
        df_data_market_all_dates = pd.DataFrame(all_dates, columns=["Dates"])

        df_data_market_all = pd.merge(data_market, df_data_market_all_dates, left_on="Date", right_on="Dates", how="right")
        df_data_market_all.drop("Date", axis=1, inplace=True)

        # fwd fill data to avoid na
        df_data_market_all.ffill(axis=0,inplace=True)

        # get month ends
        idx = df_data_market_all.Dates.dt.is_month_end
        df_data_market_all = df_data_market_all.loc[idx]
        df_data_market_all.drop("Dates", axis=1, inplace=True)

        # drop tickers with no price history at all (e.g. UBLB.F) — all-NaN columns
        # would cause dropna(axis=0) below to remove every row
        df_data_market_all = df_data_market_all.dropna(axis=1, how="all")

        # get returns from prices
        df_returns = df_data_market_all.pct_change()
        expected_returns = df_returns.mean()


        # covariance calculations
        self.df_sample_cov_matrix = df_returns.cov()
        cov = LedoitWolf().fit(df_returns.dropna())
        self.df_LedoitWolf_cov_matrix = pd.DataFrame(cov.covariance_, index=df_returns.columns, columns=df_returns.columns)

        # max sharpe ratio optim - objective function
        def max_sharpe_ratio(weights, cov_matrix):
            portfolio_return = np.dot(weights, expected_returns)
            portfolio_volatility = np.dot(weights.transpose(), np.dot(cov_matrix, weights)) ** 1/2
            msr = (portfolio_return - self.risk_free_rate/12) / portfolio_volatility
            return -msr

        constraints = ({'type': 'eq', 'fun': lambda weights: np.sum(weights) - 1})
        bounds = tuple((0, 1) for _ in range(len(expected_returns)))
        initial_weights = np.array([1 / len(expected_returns)] * len(expected_returns))
        result_sample = minimize(max_sharpe_ratio, initial_weights, args=(self.df_sample_cov_matrix), method='SLSQP', bounds=bounds, constraints=constraints)
        result_lw = minimize(max_sharpe_ratio, initial_weights, args=(self.df_LedoitWolf_cov_matrix), method='SLSQP', bounds=bounds, constraints=constraints)

        df_weights = pd.DataFrame({
            'Asset': df_data_market_all.columns,
            'Weight_Sample': result_sample.x,
            'Weight_LW': result_lw.x,
        })

        df_weights["Weight_Sample"] = df_weights["Weight_Sample"].apply(lambda x: 0 if x < 1e-6 else x)
        df_weights["Weight_LW"] = df_weights["Weight_LW"].apply(lambda x: 0 if x < 1e-6 else x)

        df_to_write = df_weights.loc[:,["Asset","Weight_LW"]]
        df_to_write.columns = ["Symbol","Weights"]
        WeightsValidator(weights=df_to_write)
        df_to_write.to_csv(fullpath( self.path_strategy("msr"),
                                                  get_datestr(self.current_date)+".csv" ), index=False)

        return prior_weights, df_weights


class PCAMaxSharpeRatioPortfolio(BaseStrategy):

    """
    Strategy C: PCA-enhanced MSR.

    Reduces the N-stock return space to k principal components (auto-selected
    by explained variance threshold), estimates a cleaner LedoitWolf covariance
    in that lower-dimensional space, runs the MSR optimiser on the factors, then
    projects the factor weights back to individual stocks.

    Compared to plain MSR (Strategy B), this produces more diversified weights
    because the optimiser works on a well-conditioned k×k covariance rather than
    a noisy N×N one.
    """

    def __init__(self, current_date, variance_threshold=0.90):
        self.inception_date = validate_date("2020-12-31")
        self.current_date = validate_date(current_date)
        self.last_day = last_day(self.current_date)
        self.last_working_day = last_working_day(self.current_date)
        self.module = "pca"
        self.market_module = "prices"
        self.risk_free_rate = 0.035
        self.variance_threshold = variance_threshold
        DateConfig(current_date=self.current_date)

    def calculate_weights(self):

        [data_market, prior_weights] = self.prepare_strategy()

        # ── same preprocessing as MSR ──────────────────────────────────────
        data_market["Date"] = pd.to_datetime(data_market["Date"])
        start_date, end_date = data_market.iloc[[0, -1]]["Date"].values
        all_dates = pd.date_range(start=start_date, end=end_date)
        df_all = pd.merge(
            data_market,
            pd.DataFrame(all_dates, columns=["Dates"]),
            left_on="Date", right_on="Dates", how="right"
        )
        df_all.drop("Date", axis=1, inplace=True)
        df_all.ffill(axis=0, inplace=True)
        df_all = df_all.loc[df_all.Dates.dt.is_month_end]
        df_all.drop("Dates", axis=1, inplace=True)
        df_all = df_all.dropna(axis=1, how="all")

        df_returns = df_all.pct_change().dropna()
        stocks = df_returns.columns.tolist()
        N = len(stocks)

        # ── auto-select k via explained variance ───────────────────────────
        pca_full = PCA().fit(df_returns.values)
        cumvar = np.cumsum(pca_full.explained_variance_ratio_)
        k = int(np.searchsorted(cumvar, self.variance_threshold)) + 1
        k = min(k, N - 1, len(df_returns) - 1)

        self.n_components_used = k
        self.explained_variance_pct = cumvar[k - 1]
        self.explained_variance_ratio_ = pca_full.explained_variance_ratio_

        # ── PCA: reduce to k factors ───────────────────────────────────────
        pca = PCA(n_components=k)
        factor_returns = pca.fit_transform(df_returns.values)  # (T, k)
        loadings = pca.components_.T                           # (N, k)

        # ── LedoitWolf covariance in factor space ──────────────────────────
        lw = LedoitWolf().fit(factor_returns)
        cov_pc = lw.covariance_                                # (k, k)

        # ── expected returns projected to factor space ─────────────────────
        mu_stocks = df_returns.mean().values                   # (N,)
        mu_pc = loadings.T @ mu_stocks                         # (k,)

        # ── MSR optimisation in PC space ───────────────────────────────────
        def neg_sharpe(w, cov):
            ret = np.dot(w, mu_pc)
            vol = np.sqrt(np.dot(w, np.dot(cov, w)))
            return -(ret - self.risk_free_rate / 12) / vol

        init_w = np.ones(k) / k
        result = minimize(
            neg_sharpe, init_w, args=(cov_pc,), method="SLSQP",
            bounds=[(0, 1)] * k,
            constraints=[{"type": "eq", "fun": lambda w: np.sum(w) - 1}]
        )
        w_pc = result.x                                        # (k,)

        # ── project back to stock space ────────────────────────────────────
        w_stocks = loadings @ w_pc                             # (N,)
        w_stocks = np.maximum(w_stocks, 0)                     # long-only
        w_stocks /= w_stocks.sum()                             # renormalise

        df_weights = pd.DataFrame({"Asset": stocks, "Weight_PCA": w_stocks})
        df_weights["Weight_PCA"] = df_weights["Weight_PCA"].apply(
            lambda x: 0.0 if x < 1e-6 else x
        )
        # renormalise after zeroing tiny weights
        total = df_weights["Weight_PCA"].sum()
        if total > 0:
            df_weights["Weight_PCA"] /= total

        df_to_write = df_weights.rename(columns={"Asset": "Symbol", "Weight_PCA": "Weights"})
        WeightsValidator(weights=df_to_write)
        df_to_write.to_csv(
            fullpath(self.path_strategy("pca"), get_datestr(self.current_date) + ".csv"),
            index=False
        )

        return prior_weights, df_weights
