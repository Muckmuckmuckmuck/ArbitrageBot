from __future__ import annotations

import asyncio
import logging
from decimal import Decimal
from typing import Dict, Optional, Tuple

from .exchange import RestExchangeClient
from .strategy import QuoteIntent

logger = logging.getLogger(__name__)


class ExecutionManager:
    """Handles order submission and cancellation while remaining maker-only."""

    def __init__(self, client: RestExchangeClient, symbol: str) -> None:
        self._client = client
        self._symbol = symbol
        self._open_orders: Dict[str, Tuple[str, Decimal, Decimal]] = {}
        self._lock = asyncio.Lock()

    async def sync(self, intent: QuoteIntent) -> None:
        async with self._lock:
            await self._cancel_all()
            tasks = []
            if intent.post_buy:
                tasks.append(self._submit("buy", intent.buy_size, intent.buy_price))
            if intent.post_sell:
                tasks.append(self._submit("sell", intent.sell_size, intent.sell_price))
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

    async def _submit(self, side: str, amount: Decimal, price: Decimal) -> None:
        if amount <= 0:
            return
        try:
            order = await self._client.create_limit_order(self._symbol, side, amount, price, post_only=True)
            order_id = str(order.get("id") or order.get("order_id") or order.get("clientOrderId"))
            if order_id:
                self._open_orders[order_id] = (side, amount, price)
                logger.info("[EXECUTE] %s %s amount=%s price=%s", side.upper(), self._symbol, amount, price)
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("Failed to submit %s order for %s: %s", side, self._symbol, exc)

    async def _cancel_all(self) -> None:
        if not self._open_orders:
            return
        pending = [self._client.cancel_order(order_id, self._symbol) for order_id in list(self._open_orders)]
        for task in asyncio.as_completed(pending):
            try:
                await task
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("Cancel failed for %s: %s", self._symbol, exc)
        self._open_orders.clear()
