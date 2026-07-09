"""Turn a target-weight book into concrete orders given current account state.

Pure and broker-agnostic (so it's unit-testable): computes the dollar gap between
the target and current holdings for each symbol and emits an order only when the gap
clears a minimum-trade threshold (to keep turnover/costs down). Sells are clamped so
we never sell more than we hold; a hard single-position cap is applied as a final
guard on top of whatever the risk engine already enforced.
"""
from __future__ import annotations

from typing import Dict, List, Mapping, Optional

import pandas as pd

from quantbot.broker.base import Order


def _price(prices, symbol: str) -> float:
    try:
        val = prices[symbol]
    except (KeyError, TypeError):
        val = prices.get(symbol, 0.0) if isinstance(prices, Mapping) else 0.0
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0


def compute_orders(
    target_weights: pd.Series,
    equity: float,
    positions: Dict[str, float],
    prices,
    min_trade_usd: float = 50.0,
    allow_fractional: bool = False,
    max_single_position_pct: Optional[float] = None,
) -> List[Order]:
    tw = target_weights.copy()
    if max_single_position_pct is not None:
        tw = tw.clip(upper=max_single_position_pct)

    symbols = sorted(set(tw[tw > 0].index) | set(positions))
    orders: List[Order] = []
    for sym in symbols:
        price = _price(prices, sym)
        if price <= 0:
            continue
        target_dollars = float(tw.get(sym, 0.0)) * equity
        current_shares = float(positions.get(sym, 0.0))
        delta_dollars = target_dollars - current_shares * price
        if abs(delta_dollars) < min_trade_usd:
            continue

        raw_shares = delta_dollars / price
        shares = raw_shares if allow_fractional else float(int(raw_shares))  # truncate toward 0 (never overshoot)
        if shares < 0:  # never sell more than we hold
            shares = max(shares, -current_shares)
        if abs(shares) < (1e-9 if allow_fractional else 1.0):
            continue

        side = "BUY" if shares > 0 else "SELL"
        orders.append(Order(sym, side, abs(shares), price, abs(shares) * price))
    return orders
