"""Hard risk limits. These clamp any proposed weight book and enforce a portfolio
drawdown kill-switch. This layer sits BELOW strategies/allocator/AI — it can only
reduce risk, never increase it, and cannot be overridden at runtime.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantbot.config import RiskLimits


def enforce_caps(weights: pd.DataFrame, limits: RiskLimits) -> pd.DataFrame:
    """Clamp per-asset weight to the single-position cap and scale any row whose gross
    exceeds the gross-exposure cap back down to it."""
    w = weights.clip(lower=0.0, upper=limits.max_single_position_pct)
    gross = w.sum(axis=1)
    over = gross > limits.max_gross_exposure_pct
    if over.any():
        scale = pd.Series(1.0, index=w.index)
        scale[over] = limits.max_gross_exposure_pct / gross[over]
        w = w.mul(scale, axis=0)
    return w


def drawdown_kill_switch(
    weights: pd.DataFrame,
    prices: pd.DataFrame,
    max_drawdown: float,
    reenter_recovery: float = 0.5,
) -> pd.DataFrame:
    """Path-dependent overlay: if portfolio drawdown from its peak breaches
    `max_drawdown`, force cash until it recovers `reenter_recovery` of the lost ground.
    Simulated day-by-day because the decision depends on realized equity.
    """
    rets = prices.pct_change().fillna(0.0)
    w = weights.copy()
    dates = w.index
    equity = 1.0
    peak = 1.0
    halted = False
    trough = 1.0
    prev = pd.Series(0.0, index=w.columns)
    for i, dt in enumerate(dates):
        # apply yesterday's (possibly halted) weights to today's return
        day_ret = float((prev * rets.loc[dt]).sum())
        equity *= (1.0 + day_ret)
        peak = max(peak, equity)
        dd = equity / peak - 1.0
        if not halted and dd <= -abs(max_drawdown):
            halted = True
            trough = equity
        if halted:
            trough = min(trough, equity)
            # recovered enough of the drop back toward the peak?
            if equity >= trough + reenter_recovery * (peak - trough):
                halted = False
        if halted:
            w.iloc[i] = 0.0  # go to cash
        prev = w.iloc[i]
    return w
