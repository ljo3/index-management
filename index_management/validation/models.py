from datetime import datetime

import pandas as pd
from pydantic import BaseModel, ConfigDict, field_validator

INCEPTION_DATE = datetime(2020, 12, 31)
VALID_INTERVALS = frozenset(
    {"1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo"}
)
VALID_MODULES = frozenset({"cw", "msr"})


class DateConfig(BaseModel):
    current_date: datetime

    @field_validator("current_date")
    @classmethod
    def validate_current_date(cls, v: datetime) -> datetime:
        if v.date() <= INCEPTION_DATE.date():
            raise ValueError(
                f"current_date {v.date()} must be after inception {INCEPTION_DATE.date()}"
            )
        if v.date() > datetime.now().date():
            raise ValueError(f"current_date {v.date()} is in the future")
        return v


class MarketConfig(DateConfig):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    universe: pd.DataFrame
    interval: str = "1d"

    @field_validator("universe")
    @classmethod
    def validate_universe(cls, v: pd.DataFrame) -> pd.DataFrame:
        if v.empty:
            raise ValueError("universe DataFrame is empty")
        if "symbol" not in v.columns:
            raise ValueError("universe DataFrame must have a 'symbol' column")
        if v["symbol"].isnull().any():
            raise ValueError("universe contains null symbols")
        return v

    @field_validator("interval")
    @classmethod
    def validate_interval(cls, v: str) -> str:
        if v not in VALID_INTERVALS:
            raise ValueError(f"interval '{v}' must be one of {sorted(VALID_INTERVALS)}")
        return v


class ValuationConfig(DateConfig):
    module: str

    @field_validator("module")
    @classmethod
    def validate_module(cls, v: str) -> str:
        if v not in VALID_MODULES:
            raise ValueError(f"module '{v}' must be one of {VALID_MODULES}")
        return v


class WeightsValidator(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    weights: pd.DataFrame

    @field_validator("weights")
    @classmethod
    def validate_weights(cls, v: pd.DataFrame) -> pd.DataFrame:
        if v.empty:
            raise ValueError("weights DataFrame is empty")
        if "Symbol" not in v.columns or "Weights" not in v.columns:
            raise ValueError("weights DataFrame must have 'Symbol' and 'Weights' columns")
        if v["Weights"].isnull().any():
            raise ValueError("weights contain NaN values")
        if (v["Weights"] < 0).any():
            raise ValueError("weights contain negative values")
        total = v["Weights"].sum()
        if abs(total - 1.0) > 1e-4:
            raise ValueError(f"weights sum to {total:.6f}, expected 1.0 ± 1e-4")
        return v
