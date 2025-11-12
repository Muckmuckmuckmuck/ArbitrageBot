from __future__ import annotations

import time
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Deque, Dict, Optional
from collections import deque


@dataclass
class InventoryLot:
    amount: Decimal
    price: Decimal
    timestamp: float


@dataclass
class PairRuntimeState:
    """Rolling state for a single trading pair."""

    last_quote_ts: float = 0.0
    loss_streak: int = 0
    win_streak: int = 0
    recent_fills: Deque[float] = field(default_factory=lambda: deque(maxlen=60))
    last_edge_bps: Decimal = Decimal("0")
    last_latency_ms: float = 0.0
    last_result: Optional[str] = None
    probe_size_usd: Decimal = Decimal("5")
    cooldown_until: float = 0.0
    inventory: Deque[InventoryLot] = field(default_factory=deque)

    def record_fill(self, side: str, amount: Decimal, price: Decimal, latency_ms: float, pnl: Decimal) -> None:
        now = time.time()
        self.recent_fills.append(now)
        self.last_latency_ms = latency_ms
        self.last_edge_bps = (pnl / price * Decimal("10000")) if price > 0 else Decimal("0")
        if pnl > 0:
            self.win_streak += 1
            self.loss_streak = 0
            self.last_result = "win"
        elif pnl < 0:
            self.loss_streak += 1
            self.win_streak = 0
            self.last_result = "loss"
        else:
            self.last_result = "flat"

        lot = InventoryLot(amount=amount, price=price, timestamp=now)
        if side.lower() == "buy":
            self.inventory.append(lot)
        else:
            # remove from inventory FIFO
            remaining = amount
            while remaining > 0 and self.inventory:
                head = self.inventory[0]
                take = min(head.amount, remaining)
                head.amount -= take
                remaining -= take
                if head.amount <= 0:
                    self.inventory.popleft()


@dataclass
class AccountState:
    balances: Dict[str, Decimal] = field(default_factory=dict)

    def update_balance(self, currency: str, amount: Decimal) -> None:
        self.balances[currency] = amount
