"""Shared, research-grounded building blocks for all sleeves.

References:
  - Moskowitz, Ooi & Pedersen (2012) "Time Series Momentum" — 12-1 signal, size = target_vol/sigma.
  - Barroso & Santa-Clara (2015) "Momentum has its moments" — scale by forecast vol to kill crashes.
  - Moreira & Muir (2017) "Volatility-Managed Portfolios" — cut exposure when vol is high.
  - Qian (2005) risk parity / inverse-vol weighting.
  - Faber (2007) 10-month SMA trend filter.
"""
from __future__ import annotations

from typing import Callable, Optional

import numpy as np
import pandas as pd

from quantbot.strategies.base import last_trading_day_per_month

TRADING_DAYS = 252


def momentum(prices: pd.DataFrame, lookback: int = 252, skip: int = 21) -> pd.DataFrame:
    """12-1 style momentum: return over `lookback` days, skipping the most recent `skip`."""
    return prices.shift(skip) / prices.shift(lookback) - 1.0


def signal_momentum(
    prices: pd.DataFrame,
    lookbacks=(63, 126, 252),
    skip: int = 21,
    vol_window: int = 60,
    vol_normalize: bool = True,
) -> pd.DataFrame:
    """Blended, optionally vol-normalized momentum signal.

    Averaging several horizons (3/6/12m) reduces single-lookback timing luck; dividing
    by volatility ranks assets by return-per-unit-risk (Moskowitz-Ooi-Pedersen). With
    lookbacks=(252,) and vol_normalize=False this reduces to plain 12-1 momentum.
    """
    lookbacks = tuple(lookbacks)
    vol = realized_vol(prices, vol_window) if vol_normalize else None
    total = None
    for lb in lookbacks:
        m = prices.shift(skip) / prices.shift(lb) - 1.0
        if vol_normalize:
            m = m / vol.replace(0.0, np.nan)
        total = m if total is None else total + m
    return total / len(lookbacks)


def realized_vol(prices: pd.DataFrame, window: int = 60) -> pd.DataFrame:
    """Annualized trailing realized volatility per asset."""
    rets = prices.pct_change()
    return rets.rolling(window, min_periods=max(5, window // 3)).std() * np.sqrt(TRADING_DAYS)


def trend_up(prices: pd.DataFrame, window: int = 200) -> pd.DataFrame:
    """Faber trend filter: price above its rolling SMA."""
    sma = prices.rolling(window, min_periods=window // 2).mean()
    return prices > sma


def inverse_vol_weights(vol_row: pd.Series) -> Optional[pd.Series]:
    """Risk-parity weights (∝ 1/σ) over the assets in `vol_row`, summing to 1."""
    v = vol_row.replace(0.0, np.nan).dropna()
    if v.empty:
        return None
    iv = 1.0 / v
    return iv / iv.sum()


def combine_weights(
    symbols,
    method: str = "equal",
    vol_row: Optional[pd.Series] = None,
    mom_row: Optional[pd.Series] = None,
) -> pd.Series:
    """Weight a selected set by one of: 'equal', 'inverse_vol', 'momentum'.

    'equal' concentrates capital in the selected winners (good for an aggressive
    sleeve); 'inverse_vol' is risk parity (good for a defensive sleeve). Falls back
    to equal weight when the requested inputs are unavailable.
    """
    symbols = list(symbols)
    if not symbols:
        return pd.Series(dtype=float)
    if method == "inverse_vol" and vol_row is not None:
        w = inverse_vol_weights(vol_row.reindex(symbols))
        if w is not None:
            return w
    if method == "momentum" and mom_row is not None:
        m = mom_row.reindex(symbols).clip(lower=0.0)
        if m.sum() > 0:
            return m / m.sum()
    return pd.Series(1.0 / len(symbols), index=symbols)


def rebalance_dates(index: pd.DatetimeIndex, freq: str = "M"):
    """Last trading day of each period. freq: 'M' month, '2W' biweekly, 'W' week."""
    ser = pd.Series(index, index=index)
    if freq in ("W", "2W"):
        iso = index.isocalendar()
        weeks = iso["week"].to_numpy()
        keys = [iso["year"].to_numpy(), weeks if freq == "W" else (weeks // 2)]
    else:  # monthly
        keys = [index.year, index.month]
    return sorted(pd.Timestamp(x) for x in ser.groupby(keys).max())


def periodic_rebalance(
    prices: pd.DataFrame, decide: Callable[[pd.Timestamp], pd.Series], freq: str = "M"
) -> pd.DataFrame:
    """Run `decide(date)->weights` on each period boundary; hold between."""
    rebal = set(rebalance_dates(prices.index, freq))
    weights = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
    current = pd.Series(0.0, index=prices.columns)
    for dt in prices.index:
        if dt in rebal:
            current = decide(dt).reindex(prices.columns).fillna(0.0)
        weights.loc[dt] = current
    return weights


def monthly_rebalance(
    prices: pd.DataFrame, decide: Callable[[pd.Timestamp], pd.Series]
) -> pd.DataFrame:
    """Back-compat wrapper: month-end rebalance."""
    return periodic_rebalance(prices, decide, "M")


def apply_vol_target(
    weights: pd.DataFrame,
    prices: pd.DataFrame,
    target_annual_vol: float = 0.10,
    window: int = 60,
    max_leverage: float = 1.0,
) -> pd.DataFrame:
    """Scale gross exposure toward a constant target vol (Moreira-Muir / Barroso-Santa-Clara).

    Long-only: the scalar is capped at `max_leverage` (default 1.0), so this can only
    *reduce* exposure (into cash) when realized vol runs hot — the crash protection.
    """
    rets = prices.pct_change().fillna(0.0)
    w_held = weights.shift(1).fillna(0.0)
    port_ret = (w_held * rets).sum(axis=1)
    rv = port_ret.rolling(window, min_periods=max(5, window // 3)).std() * np.sqrt(TRADING_DAYS)
    scalar = (target_annual_vol / rv).clip(upper=max_leverage)
    scalar = scalar.fillna(max_leverage)
    return weights.mul(scalar, axis=0)
