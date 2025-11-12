from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, Optional

from .exchange import RestExchangeClient

logger = logging.getLogger(__name__)


@dataclass
class OrderBookSnapshot:
    best_bid: Decimal
    best_ask: Decimal
    bid_depth: Decimal
    ask_depth: Decimal
    timestamp: float

    @property
    def spread_bps(self) -> Decimal:
        if self.best_bid <= 0 or self.best_ask <= 0:
            return Decimal("0")
        spread = (self.best_ask - self.best_bid) / self.best_bid
        return (spread * Decimal("10000")).quantize(Decimal("0.0001"))


class MarketDataPoller:
    """REST polling loop for depth/trade updates."""

    def __init__(self, client: RestExchangeClient, symbol: str, interval_s: float = 0.6) -> None:
        self._client = client
        self._symbol = symbol
        self._interval_s = interval_s
        self._latest_book: Optional[OrderBookSnapshot] = None
        self._running = False
        self._task: Optional[asyncio.Task[None]] = None

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        self._running = False
        if self._task:
            await self._task
            self._task = None

    async def _run(self) -> None:
        while self._running:
            try:
                book = await self._client.fetch_order_book(self._symbol, depth=5)
                bids = book.get("bids") or []
                asks = book.get("asks") or []
                if not bids or not asks:
                    logger.debug("No depth for %s", self._symbol)
                    await asyncio.sleep(self._interval_s)
                    continue
                best_bid_price, best_bid_size = bids[0]
                best_ask_price, best_ask_size = asks[0]
                snapshot = OrderBookSnapshot(
                    best_bid=Decimal(str(best_bid_price)),
                    best_ask=Decimal(str(best_ask_price)),
                    bid_depth=Decimal(str(best_bid_size)),
                    ask_depth=Decimal(str(best_ask_size)),
                    timestamp=time.time(),
                )
                self._latest_book = snapshot
            except Exception as exc:  # pragma: no cover - defensive
                logger.exception("Market data poll failed for %s: %s", self._symbol, exc)
            await asyncio.sleep(self._interval_s)

    def latest(self) -> Optional[OrderBookSnapshot]:
        return self._latest_book
