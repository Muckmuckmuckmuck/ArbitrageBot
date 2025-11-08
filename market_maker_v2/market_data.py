from __future__ import annotations

import asyncio
import statistics
import time
from collections import deque
from dataclasses import dataclass
from decimal import Decimal
from typing import Deque, Dict, Optional, Tuple

from .exchange import ExchangeClient, ExchangeError


@dataclass
class MarketSnapshot:
    mid_price: Decimal
    best_bid: Decimal
    best_ask: Decimal
    bid_size: Decimal
    ask_size: Decimal
    spread_pct: Decimal
    bid_depth_usd: Decimal
    ask_depth_usd: Decimal
    bids: list
    asks: list
    timestamp: float


class VolatilityTracker:
    def __init__(self, lookback_seconds: int = 60, max_points: int = 200) -> None:
        self.lookback_seconds = lookback_seconds
        self.prices: Deque[Tuple[float, float]] = deque(maxlen=max_points)

    def add(self, price: Decimal) -> None:
        now = time.time()
        self.prices.append((now, float(price)))
        self._trim(now)

    def _trim(self, now: float) -> None:
        cutoff = now - self.lookback_seconds
        while self.prices and self.prices[0][0] < cutoff:
            self.prices.popleft()

    def volatility(self) -> Decimal:
        if len(self.prices) < 3:
            return Decimal("0")
        values = [price for _, price in self.prices]
        log_returns = []
        for i in range(1, len(values)):
            prev = values[i - 1]
            current = values[i]
            if prev <= 0 or current <= 0:
                continue
            log_returns.append(Decimal(current).ln() - Decimal(prev).ln())
        if len(log_returns) < 2:
            return Decimal("0")
        return Decimal(str(statistics.pstdev(log_returns)))


class MarketDataFeed:
    """Polls ticker & orderbook data until websockets are introduced."""

    def __init__(
        self,
        client: ExchangeClient,
        symbol: str,
        poll_interval: float = 1.5,
        order_book_depth: int = 10,
    ) -> None:
        self.client = client
        self.symbol = symbol
        self.poll_interval = poll_interval
        self.order_book_depth = order_book_depth
        self.volatility = VolatilityTracker()
        self.snapshot: Optional[MarketSnapshot] = None
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
                ticker, book = await asyncio.gather(
                    self.client.fetch_ticker(self.symbol),
                    self.client.fetch_order_book(self.symbol, self.order_book_depth),
                )
                best_bid, bid_size = self._extract_level(book.get("bids"))
                best_ask, ask_size = self._extract_level(book.get("asks"), best=False)
                if best_bid is None or best_ask is None:
                    await asyncio.sleep(self.poll_interval)
                    continue
                bids_list = [(Decimal(str(p)), Decimal(str(q))) for p, q in (book.get("bids") or [])]
                asks_list = [(Decimal(str(p)), Decimal(str(q))) for p, q in (book.get("asks") or [])]
                mid = (best_bid + best_ask) / 2
                spread_pct = (best_ask - best_bid) / mid if mid > 0 else Decimal("0")
                bid_depth_usd = sum((p * q for p, q in bids_list))
                ask_depth_usd = sum((p * q for p, q in asks_list))
                self.snapshot = MarketSnapshot(
                    mid_price=mid,
                    best_bid=best_bid,
                    best_ask=best_ask,
                    bid_size=bid_size,
                    ask_size=ask_size,
                    spread_pct=spread_pct,
                    bid_depth_usd=bid_depth_usd,
                    ask_depth_usd=ask_depth_usd,
                    bids=[(p, q) for p, q in bids_list],
                    asks=[(p, q) for p, q in asks_list],
                    timestamp=time.time(),
                )
                self.volatility.add(mid)
                self._error = None
            except ExchangeError as exc:
                self._error = str(exc)
            await asyncio.sleep(self.poll_interval)

    def health(self) -> Tuple[bool, Optional[str]]:
        if self.snapshot is None:
            return False, "no data yet"
        age = time.time() - self.snapshot.timestamp
        if age > self.poll_interval * 3:
            return False, f"stale snapshot age={age:.2f}s"
        return True, self._error

    @staticmethod
    def _extract_level(levels: Optional[list], best: bool = True) -> Tuple[Optional[Decimal], Optional[Decimal]]:
        if not levels:
            return None, None
        price, size = levels[0]
        return Decimal(str(price)), Decimal(str(size))

