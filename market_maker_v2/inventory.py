from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, Optional

from .config import RiskConfig
from .exchange import ExchangeClient, ExchangeError


@dataclass
class PositionSnapshot:
    symbol: str
    base_balance: Decimal
    quote_balance: Decimal
    timestamp: float

    def inventory_ratio(self, mid_price: Decimal) -> Decimal:
        quote_value = self.quote_balance
        base_value = self.base_balance * mid_price
        total = quote_value + base_value
        if total <= 0:
            return Decimal("0.5")
        return base_value / total

    def imbalance_pct(self, mid_price: Decimal) -> Decimal:
        return self.inventory_ratio(mid_price) - Decimal("0.5")


class InventoryManager:
    """Tracks balances and computes skew/hedging requirements."""

    def __init__(
        self,
        client: ExchangeClient,
        base_currency: str,
        quote_currency: str,
        risk: RiskConfig,
        poll_interval: float = 10.0,
    ) -> None:
        self.client = client
        self.base_currency = base_currency
        self.quote_currency = quote_currency
        self.risk = risk
        self.poll_interval = poll_interval
        self.snapshot: Optional[PositionSnapshot] = None
        self._running = False
        self._task: Optional[asyncio.Task[None]] = None
        self._error: Optional[str] = None

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        self._running = False
        if self._task:
            await self._task

    async def _run_loop(self) -> None:
        while self._running:
            try:
                balances = await self.client.fetch_balance()
                free = balances.get("free", {})
                base_balance = Decimal(str(free.get(self.base_currency, 0)))
                quote_balance = Decimal(str(free.get(self.quote_currency, 0)))
                self.snapshot = PositionSnapshot(
                    symbol=f"{self.base_currency}/{self.quote_currency}",
                    base_balance=base_balance,
                    quote_balance=quote_balance,
                    timestamp=time.time(),
                )
                self._error = None
            except ExchangeError as exc:
                self._error = str(exc)
            await asyncio.sleep(self.poll_interval)

    def health(self) -> Optional[str]:
        return self._error

    def compute_skew(self, mid_price: Decimal) -> Decimal:
        """
        Positive skew -> too much base; negative -> too much quote.
        Bound result to [-0.5, 0.5] for sanity.
        """
        if self.snapshot is None:
            return Decimal("0")
        imbalance = self.snapshot.imbalance_pct(mid_price)
        return max(min(imbalance, Decimal("0.5")), Decimal("-0.5"))

    def should_pause(self, mid_price: Decimal, volatility: Decimal) -> Optional[str]:
        """Return reason to pause or None."""
        if self.snapshot is None:
            return "no inventory snapshot yet"
        imbalance = abs(self.snapshot.imbalance_pct(mid_price))
        if imbalance >= self.risk.max_inventory_imbalance_pct:
            return f"inventory imbalance {imbalance:.2%} exceeds limit {self.risk.max_inventory_imbalance_pct:.2%}"
        if volatility >= self.risk.volatility_pause_threshold_pct:
            return f"volatility {volatility:.2%} exceeds pause threshold {self.risk.volatility_pause_threshold_pct:.2%}"
        return None

