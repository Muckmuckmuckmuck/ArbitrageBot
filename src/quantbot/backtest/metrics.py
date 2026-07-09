"""Performance metrics on a daily-returns / equity series."""
from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def cagr(equity: pd.Series) -> float:
    if len(equity) < 2:
        return float("nan")
    years = (equity.index[-1] - equity.index[0]).days / 365.25
    if years <= 0:
        return float("nan")
    return float((equity.iloc[-1] / equity.iloc[0]) ** (1 / years) - 1)


def ann_vol(returns: pd.Series) -> float:
    return float(returns.std() * np.sqrt(TRADING_DAYS))


def sharpe(returns: pd.Series, rf: float = 0.0) -> float:
    sd = returns.std()
    if sd == 0 or np.isnan(sd):
        return float("nan")
    excess = returns.mean() - rf / TRADING_DAYS
    return float(np.sqrt(TRADING_DAYS) * excess / sd)


def sortino(returns: pd.Series, rf: float = 0.0) -> float:
    downside = returns[returns < 0].std()
    if downside == 0 or np.isnan(downside):
        return float("nan")
    excess = returns.mean() - rf / TRADING_DAYS
    return float(np.sqrt(TRADING_DAYS) * excess / downside)


def max_drawdown(equity: pd.Series) -> float:
    peak = equity.cummax()
    return float((equity / peak - 1.0).min())


def calmar(equity: pd.Series) -> float:
    mdd = abs(max_drawdown(equity))
    return float(cagr(equity) / mdd) if mdd > 0 else float("nan")


def total_return(equity: pd.Series) -> float:
    return float(equity.iloc[-1] / equity.iloc[0] - 1) if len(equity) > 1 else float("nan")


def summary(equity: pd.Series, returns: pd.Series, rf: float = 0.0) -> dict:
    return {
        "TotalReturn": total_return(equity),
        "CAGR": cagr(equity),
        "AnnVol": ann_vol(returns),
        "Sharpe": sharpe(returns, rf),
        "Sortino": sortino(returns, rf),
        "MaxDD": max_drawdown(equity),
        "Calmar": calmar(equity),
    }
