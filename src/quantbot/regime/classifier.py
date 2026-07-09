"""Rule-based market-regime classifier (trend x volatility).

Deliberately simple and interpretable so backtests are explainable and Claude can
reason about per-regime behavior from the tracked logs. Can be upgraded to an HMM
or ML classifier later behind the same interface.

Regimes (from a benchmark, default SPY):
    bull_calm       trend up,   low vol   -> favor high-growth/momentum
    bull_volatile   trend up,   high vol  -> momentum but trim size
    bear_calm       trend down, low vol   -> favor safe-growth
    bear_volatile   trend down, high vol  -> de-risk hard
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def classify(
    benchmark_close: pd.Series,
    sma_window: int = 200,
    vol_window: int = 20,
    vol_lookback: int = 252,
) -> pd.DataFrame:
    close = benchmark_close.dropna().astype(float)
    sma = close.rolling(sma_window).mean()
    trend_up = close > sma

    ret = close.pct_change()
    rvol = ret.rolling(vol_window).std() * np.sqrt(252)
    vol_ref = rvol.rolling(vol_lookback).median()
    turbulent = rvol > vol_ref

    def label(t, v) -> str:
        if pd.isna(t) or pd.isna(v):
            return "unknown"
        if t and not v:
            return "bull_calm"
        if t and v:
            return "bull_volatile"
        if (not t) and (not v):
            return "bear_calm"
        return "bear_volatile"

    out = pd.DataFrame(
        {
            "close": close,
            "sma": sma,
            "trend_up": trend_up,
            "rvol": rvol,
            "turbulent": turbulent,
        }
    )
    out["regime"] = [label(t, v) for t, v in zip(trend_up, turbulent)]
    out["risk_on"] = trend_up.fillna(False)
    return out
