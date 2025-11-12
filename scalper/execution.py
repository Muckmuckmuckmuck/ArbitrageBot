from __future__ import annotations

import asyncio
import logging
import time
from decimal import Decimal, ROUND_DOWN
from typing import Dict, Iterable, Optional

from .exchange import RestExchangeClient
from .strategy import QuoteIntent

logger = logging.getLogger(__name__)


class ExecutionManager:
    """Handles order submission and cancellation while remaining maker-only."""

    def __init__(self, client: RestExchangeClient, symbol: str) -> None:
        self._client = client
        self._symbol = symbol
        self._quote_orders: Dict[str, Dict[str, Decimal]] = {}
        self._hedge_orders: Dict[str, Dict[str, Decimal]] = {}
        self._lock = asyncio.Lock()

    async def sync_quotes(self, intent: QuoteIntent) -> None:
        async with self._lock:
            await self._cancel_orders(list(self._quote_orders.keys()))
            self._quote_orders.clear()
            tasks = []
            if intent.post_buy:
                tasks.append(self._submit("buy", intent.buy_size, intent.buy_price, tag="quote"))
            if intent.post_sell:
                tasks.append(self._submit("sell", intent.sell_size, intent.sell_price, tag="quote"))
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

    async def cancel_all_quotes(self) -> None:
        async with self._lock:
            await self._cancel_orders(list(self._quote_orders.keys()))
            self._quote_orders.clear()

    async def cancel_all(self) -> None:
        async with self._lock:
            all_orders = list(self._quote_orders.keys()) + list(self._hedge_orders.keys())
            await self._cancel_orders(all_orders)
            self._quote_orders.clear()
            self._hedge_orders.clear()

    async def place_hedge(self, side: str, amount: Decimal, price: Decimal) -> Optional[str]:
        if amount <= 0:
            return None
        async with self._lock:
            same_side = [oid for oid, meta in self._hedge_orders.items() if meta.get("side") == side]
            if same_side:
                await self._cancel_orders(same_side)
                for oid in same_side:
                    self._hedge_orders.pop(oid, None)
            return await self._submit(side, amount, price, tag="hedge")

    async def prune_stale_hedges(self, max_age: float) -> None:
        if max_age <= 0:
            return
        threshold = time.time() - max_age
        async with self._lock:
            stale = [oid for oid, meta in self._hedge_orders.items() if meta.get("created", 0.0) < threshold]
            if stale:
                for oid in stale:
                    meta = self._hedge_orders.pop(oid, None)
                    if not meta:
                        continue
                    try:
                        await self._client.cancel_order(oid, self._symbol)
                    except Exception:
                        pass
                    await self._reprice_hedge(meta)

    def mark_filled(self, order_id: Optional[str]) -> None:
        if not order_id:
            return
        if order_id in self._quote_orders:
            self._quote_orders.pop(order_id, None)
        if order_id in self._hedge_orders:
            self._hedge_orders.pop(order_id, None)

    async def _submit(self, side: str, amount: Decimal, price: Decimal, *, tag: str, post_only: bool = True) -> Optional[str]:
        if amount <= 0:
            return None
        try:
            order = await self._client.create_limit_order(self._symbol, side, amount, price, post_only=post_only)
            order_id = str(order.get("id") or order.get("order_id") or order.get("clientOrderId"))
            if order_id:
                meta = {"side": side, "amount": amount, "price": price, "created": time.time()}
                if tag == "quote":
                    self._quote_orders[order_id] = meta
                else:
                    self._hedge_orders[order_id] = meta
                logger.info("[EXECUTE] %s %s amount=%s price=%s tag=%s", side.upper(), self._symbol, amount, price, tag)
            return order_id if order_id else None
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("Failed to submit %s order for %s: %s", side, self._symbol, exc)
            return None

    async def _cancel_orders(self, order_ids: Iterable[str]) -> None:
        ids = list(order_ids)
        if not ids:
            return
        for order_id in ids:
            try:
                await self._client.cancel_order(order_id, self._symbol)
            except Exception as exc:  # pragma: no cover - defensive
                logger.debug("Cancel failed for %s order=%s: %s", self._symbol, order_id, exc)

    async def _reprice_hedge(self, meta: Dict[str, Decimal]) -> None:
        side = str(meta.get("side", ""))
        amount = Decimal(str(meta.get("amount", 0)))
        if amount <= 0 or side not in {"buy", "sell"}:
            return
        try:
            book = await self._client.fetch_order_book(self._symbol, depth=1)
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug("Failed to fetch order book for hedge repricing %s: %s", self._symbol, exc)
            return

        target_price = meta.get("price", Decimal("0"))
        try:
            if side == "sell":
                best_bid = Decimal(str(book.get("bids", [[0]])[0][0])) if book.get("bids") else None
                if best_bid and best_bid > 0:
                    target_price = (best_bid * Decimal("0.999")).quantize(Decimal("0.00001"), rounding=ROUND_DOWN)
            else:
                best_ask = Decimal(str(book.get("asks", [[0]])[0][0])) if book.get("asks") else None
                if best_ask and best_ask > 0:
                    target_price = (best_ask * Decimal("1.001")).quantize(Decimal("0.00001"), rounding=ROUND_DOWN)
        except Exception:
            pass

        await self._submit(side, amount, target_price, tag="hedge", post_only=False)
