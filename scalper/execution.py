from __future__ import annotations

import asyncio
import logging
import time
from decimal import Decimal, ROUND_DOWN
from typing import Dict, Iterable, Optional

from ccxt.base.errors import InsufficientFunds  # type: ignore
from .exchange import RestExchangeClient
from .strategy import QuoteIntent
from .config import EngineSettings

logger = logging.getLogger(__name__)


class ExecutionManager:
    """Handles order submission and cancellation while remaining maker-only."""

    def __init__(self, client: RestExchangeClient, symbol: str, settings: EngineSettings) -> None:
        self._client = client
        self._symbol = symbol
        self._settings = settings
        self._quote_orders: Dict[str, Dict[str, Decimal]] = {}
        self._hedge_orders: Dict[str, Dict[str, Decimal]] = {}
        self._lock = asyncio.Lock()

    async def sweep_orphans(self, *, force_age_cancel_s: float = 90.0) -> None:
        """
        Cancel any open exchange orders we are not tracking, and force-cancel aged ones.
        CRITICAL: NEVER cancel protective sell hedges (those with min_price set after a buy fill).
        """
        async with self._lock:
            try:
                open_orders = await self._client.fetch_open_orders(self._symbol)
            except Exception as exc:  # pragma: no cover - defensive
                logger.debug("[SWEEP] fetch_open_orders failed for %s: %s", self._symbol, exc)
                return
            if not isinstance(open_orders, list):
                return
            known_ids = set(self._quote_orders.keys()) | set(self._hedge_orders.keys())
            now = time.time()
            to_cancel: list[str] = []
            for order in open_orders:
                oid = str(order.get("id") or order.get("order_id") or order.get("clientOrderId") or "")
                if not oid:
                    continue
                ctime = float(order.get("timestamp") or order.get("datetime_ms") or 0) / 1000.0
                if oid not in known_ids:
                    to_cancel.append(oid)
                    continue
                # CRITICAL: NEVER cancel protective sell hedges (those with min_price set)
                # These are protecting filled buy orders and must remain active
                meta = self._quote_orders.get(oid) or self._hedge_orders.get(oid) or {}
                side = str(meta.get("side", "")).lower()
                if side == "sell" and meta.get("min_price") is not None:
                    # This is a protective sell hedge - NEVER cancel it
                    logger.debug("[SWEEP] Protecting sell hedge %s (min_price=%s) from cancellation", oid, meta.get("min_price"))
                    continue
                # Force-cancel tracked orders older than threshold (except protective hedges)
                created = float(meta.get("created", now))
                if force_age_cancel_s > 0 and (now - created) >= force_age_cancel_s:
                    to_cancel.append(oid)
            if to_cancel:
                await self._cancel_orders(to_cancel)
                for oid in to_cancel:
                    if oid in self._quote_orders:
                        self._quote_orders.pop(oid, None)
                    if oid in self._hedge_orders:
                        self._hedge_orders.pop(oid, None)
                logger.info("[SWEEP] cancelled=%s symbol=%s", len(to_cancel), self._symbol)

    async def sweep_orphaned_inventory(
        self,
        wallet_base: Decimal,
        tracked_inventory: Decimal,
        min_price: Decimal,
        pair_min_notional: Decimal,
    ) -> Optional[str]:
        """
        Sweep for crypto in wallet without an active sell order.
        If crypto is found without a protective sell order, place one immediately.
        Returns order_id if placed, None otherwise.
        """
        if wallet_base <= 0:
            return None
        
        # Check if we have active sell hedge orders
        async with self._lock:
            active_sell_hedges = [
                (oid, meta)
                for oid, meta in self._hedge_orders.items()
                if str(meta.get("side", "")).lower() == "sell"
            ]
            total_hedged = sum(Decimal(str(meta.get("amount", 0))) for _, meta in active_sell_hedges)
            
            # Calculate unhedged inventory
            unhedged = wallet_base - total_hedged
            if unhedged <= 0:
                return None
            
            # Check if unhedged amount meets minimum notional
            unhedged_notional = unhedged * min_price
            if unhedged_notional < pair_min_notional:
                logger.debug(
                    "[SWEEPER] Unhedged inventory %s %s (value=%s) below min_notional=%s, skipping",
                    self._symbol,
                    unhedged,
                    unhedged_notional,
                    pair_min_notional,
                )
                return None
            
            # We have unhedged crypto - place a protective sell order immediately
            # Use min_price to ensure we're profitable
            amount = self._client.amount_to_precision(self._symbol, unhedged)
            if amount <= 0:
                return None
            
            logger.warning(
                "[SWEEPER] Found unhedged inventory %s %s (value=%s) without sell order! Placing protective sell immediately.",
                self._symbol,
                amount,
                unhedged_notional,
            )
            
            # Place sell hedge at min_price to protect the position
            order_id = await self._submit("sell", amount, min_price, tag="hedge", post_only=True)
            if order_id and order_id in self._hedge_orders:
                meta = self._hedge_orders[order_id]
                meta["min_price"] = min_price  # Mark as protective hedge
                meta.setdefault("original_amount", amount)
                meta.setdefault("created_ts", meta.get("created", time.time()))
                meta.setdefault("stage", 0)
                logger.info(
                    "[SWEEPER] Placed protective sell order %s for %s %s at price %s",
                    order_id,
                    self._symbol,
                    amount,
                    min_price,
                )
            return order_id

    async def sync_quotes(self, intent: QuoteIntent) -> None:
        async with self._lock:
            desired = {}
            if intent.post_buy:
                desired_amount = self._client.amount_to_precision(self._symbol, intent.buy_size)
                desired_price = self._client.price_to_precision(self._symbol, intent.buy_price)
                desired["buy"] = {"amount": desired_amount, "price": desired_price}
            if intent.post_sell:
                desired_amount = self._client.amount_to_precision(self._symbol, intent.sell_size)
                desired_price = self._client.price_to_precision(self._symbol, intent.sell_price)
                desired["sell"] = {"amount": desired_amount, "price": desired_price}

            to_cancel = []
            for order_id, meta in list(self._quote_orders.items()):
                side = str(meta.get("side", "")).lower()
                if side not in desired:
                    to_cancel.append(order_id)
                    continue
                wanted = desired[side]
                if self._orders_equivalent(meta, wanted):
                    meta["created"] = time.time()
                    desired.pop(side, None)
                else:
                    to_cancel.append(order_id)

            if to_cancel:
                await self._cancel_orders(to_cancel)
                for order_id in to_cancel:
                    self._quote_orders.pop(order_id, None)

            tasks = []
            for side, wanted in desired.items():
                tasks.append(
                    self._submit(
                        side,
                        Decimal(wanted["amount"]),
                        Decimal(wanted["price"]),
                        tag="quote",
                    )
                )
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

    async def place_hedge(
        self,
        side: str,
        amount: Decimal,
        price: Decimal,
        *,
        allow_taker: bool = False,
        min_price: Optional[Decimal] = None,
        max_price: Optional[Decimal] = None,
    ) -> Optional[str]:
        if amount <= 0:
            return None
        async with self._lock:
            same_side = [oid for oid, meta in self._hedge_orders.items() if meta.get("side") == side]
            if same_side:
                await self._cancel_orders(same_side)
                for oid in same_side:
                    self._hedge_orders.pop(oid, None)
            order_id = await self._submit(side, amount, price, tag="hedge", post_only=not allow_taker)
            if order_id and order_id in self._hedge_orders:
                meta = self._hedge_orders[order_id]
                meta["allow_taker"] = allow_taker
                if min_price is not None:
                    meta["min_price"] = min_price
                if max_price is not None:
                    meta["max_price"] = max_price
                meta.setdefault("original_amount", Decimal(str(amount)))
                meta.setdefault("created_ts", meta.get("created", time.time()))
                meta.setdefault("stage", 0)
            return order_id

    async def prune_stale_hedges(self, max_age: float) -> None:
        """
        Prune stale hedges and advance them to taker orders if needed.
        CRITICAL: Sell hedges protecting filled buys NEVER cancel - only repost if price moves significantly.
        Only cancels hedges that are truly stale (older than max_age) and need repricing.
        """
        if max_age <= 0:
            return
        threshold = time.time() - max_age
        async with self._lock:
            stale = []
            for oid, meta in list(self._hedge_orders.items()):
                created = meta.get("created", 0.0)
                if created < threshold:
                    # Check if hedge price is still reasonable
                    side = str(meta.get("side", "")).lower()
                    hedge_price = Decimal(str(meta.get("price", 0)))
                    if hedge_price <= 0:
                        stale.append(oid)
                        continue
                    
                    # CRITICAL: Sell hedges protecting filled buys NEVER cancel - only repost if price moves
                    # If this is a sell hedge with min_price set, it's protecting a filled buy
                    # We should NEVER cancel it, only repost if price dropped significantly
                    if side == "sell" and meta.get("min_price") is not None:
                        # This is a protective sell hedge - only repost if price dropped significantly
                        try:
                            best_price = await self._best_price(side)
                            if best_price is None:
                                # Can't check price, keep the hedge - NEVER cancel protective hedges
                                continue
                            
                            min_price = Decimal(str(meta.get("min_price", 0)))
                            # Only repost if current bid is significantly below min_price (unprofitable)
                            # Otherwise, keep the hedge active - it will fill eventually
                            if best_price < min_price:
                                price_diff_pct = (min_price - best_price) / min_price
                                if price_diff_pct > Decimal("0.005"):  # 50 bps - price dropped significantly
                                    # Price dropped too much, need to repost at current price
                                    stale.append(oid)
                            # Otherwise, keep the hedge - don't cancel protective sell orders
                            continue
                        except Exception:
                            # Error checking price, keep the hedge to be safe
                            continue
                    
                    # Get current best price to see if hedge is still competitive
                    try:
                        best_price = await self._best_price(side)
                        if best_price is None:
                            # Can't check price, keep the hedge
                            continue
                        
                        # For sell hedges: cancel if current bid is significantly below hedge price
                        # (meaning price dropped, our sell hedge won't fill at current price)
                        # For buy hedges: cancel if current ask is significantly above hedge price
                        # (meaning price rose, our buy hedge won't fill at current price)
                        if side == "sell":
                            # If current bid is more than 20 bps below hedge price, hedge is stale
                            # (price dropped, hedge won't fill - need to repost lower)
                            if best_price < hedge_price:
                                price_diff_pct = (hedge_price - best_price) / hedge_price
                                if price_diff_pct > Decimal("0.002"):  # 20 bps - price dropped significantly
                                    stale.append(oid)
                        elif side == "buy":
                            # If current ask is more than 20 bps above hedge price, hedge is stale
                            # (price rose, hedge won't fill - need to repost higher)
                            if best_price > hedge_price:
                                price_diff_pct = (best_price - hedge_price) / hedge_price
                                if price_diff_pct > Decimal("0.002"):  # 20 bps - price rose significantly
                                    stale.append(oid)
                        else:
                            # Unknown side, cancel if old
                            stale.append(oid)
                    except Exception:
                        # Error checking price, keep the hedge to be safe
                        continue
            
            if stale:
                for oid in stale:
                    meta = self._hedge_orders.pop(oid, None)
                    if not meta:
                        continue
                    try:
                        await self._client.cancel_order(oid, self._symbol)
                        logger.info(
                            "[HEDGE] Cancelled stale hedge %s %s side=%s age=%.1fs price=%s",
                            self._symbol,
                            oid,
                            meta.get("side"),
                            time.time() - meta.get("created", time.time()),
                            meta.get("price"),
                        )
                    except Exception:
                        pass
                    await self._advance_hedge(meta)

    async def prune_stale_quotes(self, max_age: float) -> None:
        if max_age <= 0:
            return
        threshold = time.time() - max_age
        async with self._lock:
            stale = [oid for oid, meta in self._quote_orders.items() if meta.get("created", 0.0) < threshold]
            if not stale:
                return
            await self._cancel_orders(stale)
            for oid in stale:
                self._quote_orders.pop(oid, None)

    def mark_filled(self, order_id: Optional[str]) -> Optional[Dict[str, Decimal]]:
        if not order_id:
            return None
        meta: Optional[Dict[str, Decimal]] = None
        if order_id in self._quote_orders:
            meta = self._quote_orders.pop(order_id, None)
        if order_id in self._hedge_orders:
            meta = self._hedge_orders.pop(order_id, None)
        return meta

    async def flatten_inventory(
        self,
        side: str,
        amount: Decimal,
        price: Decimal,
    ) -> Optional[str]:
        """Submit a taker order to clear small residual inventory."""
        if amount <= 0:
            return None
        async with self._lock:
            try:
                amount = self._client.amount_to_precision(self._symbol, amount)
                price = self._client.price_to_precision(self._symbol, price)
                order = await self._client.create_limit_order(
                    self._symbol,
                    side,
                    amount,
                    price,
                    post_only=False,
                )
                order_id = str(order.get("id") or order.get("order_id") or order.get("clientOrderId"))
                if order_id:
                    logger.info(
                        "[FLATTEN] %s %s amount=%s price=%s",
                        side.upper(),
                        self._symbol,
                        amount,
                        price,
                    )
                return order_id if order_id else None
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("[FLATTEN] failed %s %s amount=%s price=%s exc=%s", side.upper(), self._symbol, amount, price, exc)
                return None

    async def _submit(self, side: str, amount: Decimal, price: Decimal, *, tag: str, post_only: bool = True) -> Optional[str]:
        if amount <= 0:
            logger.debug("[EXECUTE] %s %s skipping: amount <= 0", side.upper(), self._symbol)
            return None
        if price <= 0:
            logger.warning("[EXECUTE] %s %s skipping: invalid price %s", side.upper(), self._symbol, price)
            return None
        try:
            amount = self._client.amount_to_precision(self._symbol, amount)
            if amount > 0:
                try:
                    amount = amount.quantize(Decimal("0.00000001"), rounding=ROUND_DOWN)
                except Exception:
                    pass
            price = self._client.price_to_precision(self._symbol, price)
            min_amount = self._client.min_amount(self._symbol)
            if min_amount and amount < min_amount:
                logger.debug("[EXECUTE] %s %s amount %s below min %s", side.upper(), self._symbol, amount, min_amount)
                return None
            if amount <= 0:
                logger.debug("[EXECUTE] %s %s amount became 0 after precision", side.upper(), self._symbol)
                return None
            
            # Validate order value meets minimum notional (if we can determine it)
            order_value = amount * price
            if order_value <= 0:
                logger.warning("[EXECUTE] %s %s order value %s is invalid", side.upper(), self._symbol, order_value)
                return None
            
            order = await self._client.create_limit_order(self._symbol, side, amount, price, post_only=post_only)
            order_id = str(order.get("id") or order.get("order_id") or order.get("clientOrderId"))
            if order_id:
                meta = {
                    "side": side,
                    "amount": amount,
                    "price": price,
                    "created": time.time(),
                    "tag": tag,
                }
                if tag == "quote":
                    self._quote_orders[order_id] = meta
                else:
                    self._hedge_orders[order_id] = meta
                    meta.setdefault("original_amount", amount)
                    meta.setdefault("created_ts", meta["created"])
                    meta.setdefault("stage", 0)
                logger.info("[EXECUTE] %s %s amount=%s price=%s value=%s tag=%s", side.upper(), self._symbol, amount, price, order_value.quantize(Decimal("0.01")), tag)
            return order_id if order_id else None
        except InsufficientFunds as exc:
            logger.warning(
                "[EXECUTE] %s %s insufficient funds amount=%s price=%s value=%s tag=%s exc=%s",
                side.upper(),
                self._symbol,
                amount,
                price,
                (amount * price).quantize(Decimal("0.01")),
                tag,
                exc,
            )
            return None
        except Exception as exc:  # pragma: no cover - defensive
            logger.error(
                "[EXECUTE] Failed to submit %s order for %s amount=%s price=%s tag=%s: %s",
                side,
                self._symbol,
                amount,
                price,
                tag,
                exc,
                exc_info=True,
            )
            return None

    @staticmethod
    def _orders_equivalent(existing: Dict[str, Decimal], wanted: Dict[str, Decimal]) -> bool:
        """
        Check if existing order matches desired order.
        Uses lenient matching to avoid cancelling orders due to tiny market movements.
        - Price: allows up to 5 bps (0.05%) difference
        - Amount: allows up to 1% difference
        """
        try:
            existing_price = Decimal(existing.get("price", 0))
            wanted_price = Decimal(wanted.get("price", 0))
            existing_amount = Decimal(existing.get("amount", 0))
            wanted_amount = Decimal(wanted.get("amount", 0))
            
            if existing_price <= 0 or wanted_price <= 0:
                return False
            
            # Price difference: allow up to 5 bps (0.05%) relative difference
            # This prevents cancelling orders due to tiny market movements
            price_diff_pct = abs(existing_price - wanted_price) / wanted_price
            price_match = price_diff_pct <= Decimal("0.0005")  # 5 bps = 0.05%
            
            # Amount difference: allow up to 1% relative difference
            # This handles rounding/precision differences
            if wanted_amount > 0:
                amount_diff_pct = abs(existing_amount - wanted_amount) / wanted_amount
                amount_match = amount_diff_pct <= Decimal("0.01")  # 1%
            else:
                amount_match = existing_amount == wanted_amount
            
            return price_match and amount_match
        except Exception:
            return False

    def amount_precision(self, amount: Decimal) -> Decimal:
        return self._client.amount_to_precision(self._symbol, amount)

    def min_order_amount(self) -> Optional[Decimal]:
        return self._client.min_amount(self._symbol)

    async def _cancel_orders(self, order_ids: Iterable[str]) -> None:
        ids = list(order_ids)
        if not ids:
            return
        for order_id in ids:
            try:
                await self._client.cancel_order(order_id, self._symbol)
            except Exception as exc:  # pragma: no cover - defensive
                logger.debug("Cancel failed for %s order=%s: %s", self._symbol, order_id, exc)

    async def _advance_hedge(self, meta: Dict[str, Decimal]) -> None:
        side = str(meta.get("side", ""))
        remaining = Decimal(str(meta.get("amount", 0)))
        if remaining <= 0 or side not in {"buy", "sell"}:
            return

        created_ts = float(meta.get("created_ts", meta.get("created", time.time())))
        stage = int(meta.get("stage", 0))
        now = time.time()
        elapsed = now - created_ts

        best_price = await self._best_price(side)
        if best_price is None:
            return

        min_price = meta.get("min_price")
        max_price = meta.get("max_price")
        if min_price is not None and side == "sell":
            try:
                best_price = max(best_price, Decimal(str(min_price)))
            except Exception:
                pass
        if max_price is not None and side == "buy":
            try:
                best_price = min(best_price, Decimal(str(max_price)))
            except Exception:
                pass

        min_amount = self._client.min_amount(self._symbol) or Decimal("0")
        partial_ratio = self._settings.hedge_stage_partial_ratio
        if partial_ratio < Decimal("0"):
            partial_ratio = Decimal("0")
        if partial_ratio > Decimal("1"):
            partial_ratio = Decimal("1")

        if stage == 0 and elapsed >= self._settings.hedge_stage_one_seconds and partial_ratio > 0:
            taker_amount = (remaining * partial_ratio).quantize(Decimal("0.00000001"), rounding=ROUND_DOWN)
            if min_amount > 0:
                taker_amount = max(taker_amount, min_amount)
            if taker_amount > 0 and taker_amount < remaining:
                executed = await self._execute_taker(side, taker_amount, best_price, "stage1")
                if executed:
                    remaining -= taker_amount
                    meta["stage"] = 1
                    meta["amount"] = remaining
                    meta["created"] = now
                    meta["created_ts"] = created_ts

        if remaining <= 0:
            return

        # Check if best_price violates min/max constraints (would be unprofitable)
        if min_price is not None and side == "sell" and best_price < min_price:
            # Price dropped too much - force taker to exit at best available price
            logger.warning(
                "[HEDGE] %s %s price dropped below min_price (min=%s best=%s), forcing taker exit",
                side.upper(),
                self._symbol,
                min_price,
                best_price,
            )
            await self._execute_taker(side, remaining, best_price, "price_drop")
            return
        if max_price is not None and side == "buy" and best_price > max_price:
            # Price rose too much - force taker to exit at best available price
            logger.warning(
                "[HEDGE] %s %s price rose above max_price (max=%s best=%s), forcing taker exit",
                side.upper(),
                self._symbol,
                max_price,
                best_price,
            )
            await self._execute_taker(side, remaining, best_price, "price_rise")
            return

        if elapsed >= self._settings.hedge_stage_two_seconds:
            await self._execute_taker(side, remaining, best_price, "stage2")
            return

        new_id = await self._submit(side, remaining, best_price, tag="hedge", post_only=True)
        if new_id:
            new_meta = self._hedge_orders.get(new_id)
            if new_meta is not None:
                new_meta.setdefault("original_amount", Decimal(str(meta.get("original_amount", remaining))))
                new_meta.setdefault("created_ts", created_ts)
                new_meta["stage"] = meta.get("stage", stage)
                if "min_price" in meta:
                    new_meta["min_price"] = meta["min_price"]
                if "max_price" in meta:
                    new_meta["max_price"] = meta["max_price"]
                new_meta["allow_taker"] = meta.get("allow_taker", False)

    async def _best_price(self, side: str) -> Optional[Decimal]:
        try:
            book = await self._client.fetch_order_book(self._symbol, depth=1)
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug("Failed to fetch book for hedge advance %s: %s", self._symbol, exc)
            return None
        if side == "sell":
            bids = book.get("bids") or []
            if not bids:
                return None
            price = Decimal(str(bids[0][0]))
        else:
            asks = book.get("asks") or []
            if not asks:
                return None
            price = Decimal(str(asks[0][0]))
        return price if price > 0 else None

    async def _execute_taker(self, side: str, amount: Decimal, price: Decimal, stage: str) -> bool:
        if amount <= 0 or price <= 0:
            return False
        try:
            amount = Decimal(str(self._client.amount_to_precision(self._symbol, amount)))
            price = Decimal(str(self._client.price_to_precision(self._symbol, price)))
            order = await self._client.create_limit_order(self._symbol, side, amount, price, post_only=False)
            order_id = str(order.get("id") or order.get("order_id") or order.get("clientOrderId"))
            logger.info(
                "[HEDGE] taker %s %s amount=%s price=%s stage=%s",
                side.upper(),
                self._symbol,
                amount,
                price,
                stage,
            )
            if order_id:
                self._hedge_orders.pop(order_id, None)
            return True
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning(
                "[HEDGE] taker_failed %s %s amount=%s price=%s stage=%s exc=%s",
                side.upper(),
                self._symbol,
                amount,
                price,
                stage,
                exc,
            )
            return False
