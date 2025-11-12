from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, Optional, Tuple

from .state import PairRuntimeState

logger = logging.getLogger(__name__)


@dataclass
class PairPnLStats:
    realized: Decimal = Decimal("0")
    fees: Decimal = Decimal("0")
    wins: int = 0
    losses: int = 0
    flats: int = 0
    trades: int = 0


class PnLTracker:
    """Maintains realized/fee statistics per pair."""

    def __init__(self) -> None:
        self._pairs: Dict[str, PairPnLStats] = {}

    @property
    def total_realized(self) -> Decimal:
        return sum(stats.realized for stats in self._pairs.values())

    def get_stats(self, pair_key: str) -> PairPnLStats:
        return self._pairs.setdefault(pair_key, PairPnLStats())

    def process_fill(
        self,
        pair_key: str,
        state: PairRuntimeState,
        side: str,
        amount: Decimal,
        price: Decimal,
        fee: Decimal,
    ) -> Tuple[Decimal, str]:
        side = side.lower()
        stats = self.get_stats(pair_key)
        stats.trades += 1
        now = time.time()
        state.last_fill_ts = now
        state.recent_fills.append(now)
        state.fees_paid += fee
        stats.fees += fee
        result = "buy"
        realized = Decimal("0")

        if side == "buy":
            state.push_inventory(amount, price)
            state.last_result = "buy"
            state.loss_streak = 0
            state.win_streak = 0
        elif side == "sell":
            cost_basis = state.pop_inventory(amount)
            revenue = price * amount
            realized = revenue - cost_basis - fee
            state.realized_pnl += realized
            stats.realized += realized
            if realized > 0:
                stats.wins += 1
                state.win_streak += 1
                state.loss_streak = 0
                result = "win"
            elif realized < 0:
                stats.losses += 1
                state.loss_streak += 1
                state.win_streak = 0
                result = "loss"
            else:
                stats.flats += 1
                state.loss_streak = 0
                state.win_streak = 0
                result = "flat"
            state.last_result = result
            logger.info(
                "[PNL] %s realized=%s cumulative=%s fees=%s",
                pair_key,
                realized.quantize(Decimal("0.0001")),
                state.realized_pnl.quantize(Decimal("0.0001")),
                state.fees_paid.quantize(Decimal("0.0001")),
            )
        else:
            logger.debug("Unknown fill side %s for %s", side, pair_key)

        return realized, result
