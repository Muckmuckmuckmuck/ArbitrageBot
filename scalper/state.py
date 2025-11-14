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
    processed_trade_ids: Deque[str] = field(default_factory=lambda: deque(maxlen=500))
    realized_pnl: Decimal = Decimal("0")
    fees_paid: Decimal = Decimal("0")
    last_fill_ts: float = 0.0
    last_trade_fetch_ts: int = 0
    probe_successes: int = 0
    probe_failures: int = 0
    recent_net_edges: Deque[Decimal] = field(default_factory=lambda: deque(maxlen=60))
    recent_realized: Deque[Decimal] = field(default_factory=lambda: deque(maxlen=20))
    skip_reasons: Dict[str, int] = field(default_factory=dict)
    tier_scores: Dict[str, Decimal] = field(default_factory=dict)
    current_tier: Optional[str] = None
    fill_count: int = 0
    win_count: int = 0
    loss_count: int = 0
    last_fill_latency_ms: float = 0.0
    last_fill_ts: float = 0.0
    fast_fill_bias: Decimal = Decimal("0")
    last_quote_reason: Optional[str] = None
    hedge_failure_ts: Optional[float] = None
    hedge_attempt_side: Optional[str] = None
    last_hedge_entry: Optional[Decimal] = None

    def push_inventory(self, amount: Decimal, price: Decimal) -> None:
        self.inventory.append(InventoryLot(amount=amount, price=price, timestamp=time.time()))

    def pop_inventory(self, amount: Decimal) -> Decimal:
        """Return total cost basis for the amount removed (FIFO)."""

        remaining = amount
        cost = Decimal("0")
        while remaining > 0 and self.inventory:
            lot = self.inventory[0]
            take = min(lot.amount, remaining)
            cost += take * lot.price
            lot.amount -= take
            remaining -= take
            if lot.amount <= 0:
                self.inventory.popleft()
        if remaining > 0:
            # sell without inventory—treat as zero cost
            return cost
        return cost

    def seen_trade(self, trade_id: Optional[str]) -> bool:
        if not trade_id:
            return False
        if trade_id in self.processed_trade_ids:
            return True
        self.processed_trade_ids.append(trade_id)
        return False

    def record_skip(self, reason: str) -> None:
        self.skip_reasons[reason] = self.skip_reasons.get(reason, 0) + 1

    def update_probe(self, success: bool, cfg_base: Decimal, cfg_step: Decimal, cfg_max: Decimal) -> None:
        if success:
            self.probe_successes += 1
            self.probe_failures = max(0, self.probe_failures - 1)
            next_size = min(self.probe_size_usd + cfg_step, cfg_max)
            self.probe_size_usd = next_size
        else:
            self.probe_failures += 1
            self.probe_successes = 0
            next_size = max(cfg_base, self.probe_size_usd - cfg_step)
            self.probe_size_usd = next_size

    def register_fill(self, result: str, latency_ms: float, realized: Decimal) -> None:
        self.fill_count += 1
        if result == "win":
            self.win_count += 1
        elif result == "loss":
            self.loss_count += 1
        self.last_fill_latency_ms = latency_ms
        self.last_fill_ts = time.time()
        self.recent_realized.append(realized)


@dataclass
class AccountState:
    balances: Dict[str, Decimal] = field(default_factory=dict)

    def update_balance(self, currency: str, amount: Decimal) -> None:
        self.balances[currency] = amount
