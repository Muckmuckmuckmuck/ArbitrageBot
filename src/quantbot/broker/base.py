"""Broker interface shared by the live (IBKR) and simulated brokers.

Keeping execution behind this ABC means the rebalancer and daily loop are written
once and tested against SimBroker, then run unchanged against IBKR paper/live.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict


@dataclass
class Order:
    symbol: str
    side: str            # "BUY" | "SELL"
    shares: float
    est_price: float
    est_notional: float
    status: str = "new"
    note: str = ""


class Broker(ABC):
    @abstractmethod
    def connect(self) -> None: ...

    @abstractmethod
    def disconnect(self) -> None: ...

    @abstractmethod
    def net_liquidation(self) -> float:
        """Total account equity in USD."""

    @abstractmethod
    def positions(self) -> Dict[str, float]:
        """symbol -> signed share quantity currently held."""

    @abstractmethod
    def price(self, symbol: str) -> float:
        """Best available price for `symbol` (used as a fallback; the daily loop
        prefers the shared close panel for sizing to match the backtest)."""

    @abstractmethod
    def submit(self, order: Order) -> Order:
        """Place `order`; return it with an updated status."""

    def __enter__(self) -> "Broker":
        self.connect()
        return self

    def __exit__(self, *exc) -> None:
        self.disconnect()
