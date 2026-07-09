"""In-memory simulated broker — a local paper account for testing the rebalancer
and for dry-runs before IB Gateway is configured. Marks positions against a supplied
price map and models simple commission + slippage.
"""
from __future__ import annotations

from typing import Dict, Mapping

from quantbot.broker.base import Broker, Order


class SimBroker(Broker):
    def __init__(
        self,
        equity: float,
        prices: Mapping[str, float],
        positions: Dict[str, float] | None = None,
        commission_bps: float = 1.0,
        slippage_bps: float = 5.0,
    ):
        self._prices = {k: float(v) for k, v in dict(prices).items()}
        self._pos: Dict[str, float] = dict(positions or {})
        held_value = sum(sh * self._px(s) for s, sh in self._pos.items())
        self._cash = float(equity) - held_value
        self._commission = commission_bps / 1e4
        self._slippage = slippage_bps / 1e4

    def _px(self, symbol: str) -> float:
        return float(self._prices.get(symbol, 0.0))

    def connect(self) -> None:  # nothing to connect to
        pass

    def disconnect(self) -> None:
        pass

    def net_liquidation(self) -> float:
        return self._cash + sum(sh * self._px(s) for s, sh in self._pos.items())

    def positions(self) -> Dict[str, float]:
        return {s: sh for s, sh in self._pos.items() if abs(sh) > 1e-9}

    def price(self, symbol: str) -> float:
        return self._px(symbol)

    def submit(self, order: Order) -> Order:
        px = self._px(order.symbol)
        if px <= 0:
            order.status = "rejected"
            order.note = "no price"
            return order
        fill = px * (1 + self._slippage) if order.side == "BUY" else px * (1 - self._slippage)
        notional = order.shares * fill
        commission = notional * self._commission
        if order.side == "BUY":
            self._cash -= notional + commission
            self._pos[order.symbol] = self._pos.get(order.symbol, 0.0) + order.shares
        else:
            self._cash += notional - commission
            self._pos[order.symbol] = self._pos.get(order.symbol, 0.0) - order.shares
        order.status = "filled"
        return order
