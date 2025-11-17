from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, Optional, Sequence, Tuple

from .exchange import RestExchangeClient
from .config import EngineSettings

logger = logging.getLogger(__name__)


@dataclass
class OrderBookSnapshot:
    best_bid: Decimal
    best_ask: Decimal
    bids: Tuple[Tuple[Decimal, Decimal], ...]
    asks: Tuple[Tuple[Decimal, Decimal], ...]
    bid_value_usd: Decimal
    ask_value_usd: Decimal
    top_bid_value_usd: Decimal
    top_ask_value_usd: Decimal
    timestamp: float

    @property
    def spread_bps(self) -> Decimal:
        if self.best_bid <= 0 or self.best_ask <= 0:
            return Decimal("0")
        spread = (self.best_ask - self.best_bid) / self.best_bid
        return (spread * Decimal("10000")).quantize(Decimal("0.0001"))

    @property
    def mid(self) -> Decimal:
        return (self.best_bid + self.best_ask) / Decimal("2")

    @property
    def depth_usd(self) -> Decimal:
        return min(self.bid_value_usd, self.ask_value_usd)
    
    def is_undercut(self, our_price: Decimal, side: str) -> Tuple[bool, Optional[Decimal]]:
        """
        Check if our price is undercut by the order book.
        Returns: (is_undercut, competitor_price)
        """
        if side == "sell":
            # For sell orders, we're undercut if best_ask < our_price
            if self.best_ask > 0 and self.best_ask < our_price:
                return True, self.best_ask
        elif side == "buy":
            # For buy orders, we're undercut if best_bid > our_price
            if self.best_bid > 0 and self.best_bid > our_price:
                return True, self.best_bid
        return False, None
    
    def get_queue_position(self, our_price: Decimal, side: str) -> int:
        """
        Get our position in the order book queue.
        Returns: 1 = first in queue, 2 = second, etc.
        """
        if side == "sell":
            # Count how many asks are better (lower price) than ours
            better = sum(1 for price, _ in self.asks if price < our_price)
            return better + 1
        else:  # buy
            # Count how many bids are better (higher price) than ours
            better = sum(1 for price, _ in self.bids if price > our_price)
            return better + 1


class MarketDataPoller:
    """REST polling loop for depth/trade updates."""

    def __init__(
        self,
        client: RestExchangeClient,
        symbol: str,
        settings: EngineSettings,
        interval_s: float = 0.6,
    ) -> None:
        self._client = client
        self._symbol = symbol
        self._interval_s = interval_s
        self._settings = settings
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
                depth_levels = max(5, self._settings.scanner_max_depth_levels)
                book = await self._client.fetch_order_book(self._symbol, depth=depth_levels)
                bids = book.get("bids") or []
                asks = book.get("asks") or []
                if not bids or not asks:
                    logger.debug("No depth for %s", self._symbol)
                    await asyncio.sleep(self._interval_s)
                    continue
                best_bid_price, _ = bids[0]
                best_ask_price, _ = asks[0]
                bids_decimal = self._convert_levels(bids)
                asks_decimal = self._convert_levels(asks)
                if not bids_decimal or not asks_decimal:
                    logger.debug("No valid depth levels after conversion for %s", self._symbol)
                    await asyncio.sleep(self._interval_s)
                    continue
                bid_value = self._aggregate_value(bids_decimal)
                ask_value = self._aggregate_value(asks_decimal)
                top_bid_value = bids_decimal[0][0] * bids_decimal[0][1] if bids_decimal else Decimal("0")
                top_ask_value = asks_decimal[0][0] * asks_decimal[0][1] if asks_decimal else Decimal("0")
                snapshot = OrderBookSnapshot(
                    best_bid=Decimal(str(best_bid_price)),
                    best_ask=Decimal(str(best_ask_price)),
                    bids=bids_decimal,
                    asks=asks_decimal,
                    bid_value_usd=bid_value,
                    ask_value_usd=ask_value,
                    top_bid_value_usd=top_bid_value,
                    top_ask_value_usd=top_ask_value,
                    timestamp=time.time(),
                )
                self._latest_book = snapshot
            except Exception as exc:  # pragma: no cover - defensive
                logger.exception("Market data poll failed for %s: %s", self._symbol, exc)
            await asyncio.sleep(self._interval_s)

    def latest(self) -> Optional[OrderBookSnapshot]:
        return self._latest_book

    def _convert_levels(self, levels: Sequence[Sequence[float]]) -> Tuple[Tuple[Decimal, Decimal], ...]:
        converted = []
        for raw_price, raw_qty in levels[: self._settings.scanner_max_depth_levels]:
            price = Decimal(str(raw_price))
            qty = Decimal(str(raw_qty))
            if price <= 0 or qty <= 0:
                continue
            converted.append((price, qty))
        return tuple(converted)

    def _aggregate_value(self, levels: Sequence[Tuple[Decimal, Decimal]]) -> Decimal:
        total = Decimal("0")
        for price, qty in levels:
            total += price * qty
        return total
