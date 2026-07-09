"""Daily backtest engine.

Given a price panel and a target-weight panel, simulate a portfolio with
transaction costs and interest on idle cash. Positions are lagged one day
(decided at yesterday's close, earn today's return) to avoid look-ahead bias.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd

from quantbot.backtest import metrics


@dataclass
class BacktestResult:
    equity: pd.Series          # cumulative growth of $1
    returns: pd.Series         # daily portfolio returns
    weights: pd.DataFrame      # target weights actually applied
    turnover: pd.Series        # per-day traded fraction
    stats: dict


def run_backtest(
    prices: pd.DataFrame,
    weights: pd.DataFrame,
    cost_bps: float = 5.0,
    cash_annual_rate: float = 0.04,
) -> BacktestResult:
    prices = prices.sort_index()
    rets = prices.pct_change().fillna(0.0)

    w = weights.reindex(prices.index).ffill().fillna(0.0)
    w = w.reindex(columns=prices.columns, fill_value=0.0)

    w_held = w.shift(1).fillna(0.0)                    # avoid look-ahead
    asset_ret = (w_held * rets).sum(axis=1)
    cash_w = (1.0 - w_held.sum(axis=1)).clip(lower=0.0)
    cash_ret = cash_w * (cash_annual_rate / metrics.TRADING_DAYS)

    turnover = (w - w.shift(1)).abs().sum(axis=1).fillna(0.0)
    cost = turnover * (cost_bps / 1e4)

    port_ret = asset_ret + cash_ret - cost
    equity = (1.0 + port_ret).cumprod()

    stats = metrics.summary(equity, port_ret, rf=cash_annual_rate)
    return BacktestResult(equity, port_ret, w, turnover, stats)


def buy_and_hold(prices: pd.DataFrame, symbol: str) -> BacktestResult:
    w = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
    w[symbol] = 1.0
    return run_backtest(prices, w, cost_bps=0.0, cash_annual_rate=0.0)


def returns_by_regime(returns: pd.Series, regime: pd.DataFrame) -> pd.DataFrame:
    """Attribute daily returns to regime label — a core 'multi-regime' diagnostic."""
    reg = regime["regime"].reindex(returns.index).ffill()
    df = pd.DataFrame({"ret": returns, "regime": reg}).dropna()
    grp = df.groupby("regime")["ret"]
    out = pd.DataFrame(
        {
            "days": grp.count(),
            "ann_return": (1 + grp.mean()) ** metrics.TRADING_DAYS - 1,
            "ann_vol": grp.std() * (metrics.TRADING_DAYS ** 0.5),
        }
    )
    return out.sort_values("days", ascending=False)
