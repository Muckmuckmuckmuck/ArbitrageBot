from __future__ import annotations

import asyncio
import logging
import math
import random
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP
from enum import Enum
from typing import Any, Callable, Deque, Dict, Iterable, List, Optional, Sequence, Tuple

from coinbase_gemini_exchanges import CoinbaseGeminiExchangeManager
from database_manager import DatabaseManager, TradeRecord

logger = logging.getLogger(__name__)


async def maybe_awaitable(result: Optional[Any]) -> Optional[Any]:
    if asyncio.iscoroutine(result):
        return await result
    return result


# ---------------------------------------------------------------------------
# Data models & enums
# ---------------------------------------------------------------------------


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderStatus(str, Enum):
    OPEN = "open"
    PARTIAL = "partial"
    FILLED = "filled"
    CANCELLED = "cancelled"


@dataclass(slots=True)
class PairConfig:
    exchange_id: str
    symbol: str
    order_size_usd: Decimal = Decimal("10.00")
    min_spread_bps: int = 30  # 0.30%
    max_quote_interval_s: float = 5.0
    min_depth_usd: Decimal = Decimal("10000")
    min_notional_usd: Decimal = Decimal("10.00")
    price_improve_bps: int = 5  # 0.05%
    fee_floor_bps: int = 0
    min_volume_usd: Decimal = Decimal("0")


@dataclass(slots=True)
class ManagedOrder:
    exchange_id: str
    symbol: str
    side: OrderSide
    order_id: str
    price: Decimal
    amount: Decimal
    created_at: float = field(default_factory=time.time)
    status: OrderStatus = OrderStatus.OPEN
    filled_amount: Decimal = Decimal("0")
    last_update: float = field(default_factory=time.time)
    tag: str = "quote"


@dataclass(slots=True)
class FillEvent:
    exchange_id: str
    symbol: str
    side: OrderSide
    price: Decimal
    amount: Decimal
    order_id: str
    timestamp: float


# ---------------------------------------------------------------------------
# Exchange adapter
# ---------------------------------------------------------------------------


class ExchangeManagerAdapter:
    """Thin async wrapper around CoinbaseGeminiExchangeManager."""

    def __init__(self, manager: CoinbaseGeminiExchangeManager) -> None:
        self._manager = manager

    def available_exchanges(self) -> List[str]:
        return [
            ex
            for ex in ("coinbase", "gemini")
            if self._manager.is_exchange_available(ex)
        ]

    def is_symbol_supported(self, exchange_id: str, symbol: str) -> bool:
        exchange = self._manager.get_exchange(exchange_id)
        markets = getattr(exchange, "markets", {}) or {}
        return symbol in markets

    async def create_order(
        self,
        exchange_id: str,
        symbol: str,
        side: OrderSide,
        *,
        amount: Decimal,
        price: Optional[Decimal] = None,
        order_type: str = "limit",
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict:
        logger.info(
            "[ADAPTER] create_order %s %s side=%s amount=%s price=%s type=%s",
            exchange_id.upper(),
            symbol,
            side.value,
            amount,
            price,
            order_type,
        )
        return await self._manager.create_order(
            exchange_id=exchange_id,
            symbol=symbol,
            order_type=order_type,
            side=side.value,
            amount=float(amount),
            price=float(price) if price is not None else None,
            params=params,
        )

    async def cancel_order(
        self, exchange_id: str, symbol: str, order_id: str
    ) -> None:
        logger.info(
            "[ADAPTER] cancel_order %s %s order_id=%s",
            exchange_id.upper(),
            symbol,
            order_id,
        )
        await self._manager.cancel_order(exchange_id, symbol, order_id)

    async def convert_currency(
        self,
        exchange_id: str,
        from_currency: str,
        to_currency: str,
        amount: Decimal,
    ) -> bool:
        logger.info(
            "[ADAPTER] convert_currency %s %s -> %s amount=%s",
            exchange_id.upper(),
            from_currency,
            to_currency,
            amount,
        )
        return await self._manager.convert_currency(
            exchange_id,
            from_currency,
            to_currency,
            float(amount),
        )

    async def fetch_order_book(
        self, exchange_id: str, symbol: str, depth: int = 10
    ) -> Dict:
        logger.info(
            "[ADAPTER] fetch_order_book %s %s depth=%s",
            exchange_id.upper(),
            symbol,
            depth,
        )
        return await self._manager.fetch_order_book(exchange_id, symbol, depth)

    async def fetch_open_orders(
        self, exchange_id: str, symbol: Optional[str] = None
    ) -> List[Dict]:
        logger.info(
            "[ADAPTER] fetch_open_orders %s symbol=%s",
            exchange_id.upper(),
            symbol,
        )
        return await self._manager.fetch_open_orders(exchange_id, symbol)

    async def fetch_trades(
        self,
        exchange_id: str,
        symbol: Optional[str] = None,
        since: Optional[int] = None,
    ) -> List[Dict]:
        logger.info(
            "[ADAPTER] fetch_trades %s symbol=%s since=%s",
            exchange_id.upper(),
            symbol,
            since,
        )
        return await self._manager.fetch_my_trades(exchange_id, symbol, since)

    async def fetch_ohlcv(
        self,
        exchange_id: str,
        symbol: str,
        timeframe: str = "1m",
        since: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> List[List[float]]:
        logger.info(
            "[ADAPTER] fetch_ohlcv %s %s timeframe=%s limit=%s",
            exchange_id.upper(),
            symbol,
            timeframe,
            limit,
        )
        return await self._manager.fetch_ohlcv(
            exchange_id, symbol, timeframe=timeframe, since=since, limit=limit
        )

    async def fetch_balance(self, exchange_id: str) -> Dict:
        logger.info("[ADAPTER] fetch_balance %s", exchange_id.upper())
        return await self._manager.fetch_balance(exchange_id)

    async def fetch_ticker(self, exchange_id: str, symbol: str) -> Dict:
        logger.info(
            "[ADAPTER] fetch_ticker %s %s",
            exchange_id.upper(),
            symbol,
        )
        return await self._manager.fetch_ticker(exchange_id, symbol)


# ---------------------------------------------------------------------------
# Balance cache
# ---------------------------------------------------------------------------


class BalanceCache:
    def __init__(self, adapter: ExchangeManagerAdapter, refresh_interval: float = 5.0) -> None:
        self._adapter = adapter
        self._refresh_interval = refresh_interval
        self._balances: Dict[str, Dict[str, Decimal]] = defaultdict(dict)
        self._last_refresh: Dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def get_balance(self, exchange_id: str, currency: str) -> Decimal:
        async with self._lock:
            await self._maybe_refresh(exchange_id)
            return self._balances.get(exchange_id, {}).get(currency, Decimal("0"))

    async def get_balances(self, exchange_id: str) -> Dict[str, Decimal]:
        async with self._lock:
            await self._maybe_refresh(exchange_id)
            return dict(self._balances.get(exchange_id, {}))

    async def get_equity(
        self, exchange_id: str, currencies: Optional[Iterable[str]] = None
    ) -> Decimal:
        async with self._lock:
            await self._maybe_refresh(exchange_id)
            balances = self._balances.get(exchange_id, {})
            if currencies:
                currency_set = set(currencies)
                return sum(
                    balances.get(currency, Decimal("0")) for currency in currency_set
                )
            return sum(balances.values())

    async def _maybe_refresh(self, exchange_id: str) -> None:
        now = time.time()
        if now - self._last_refresh.get(exchange_id, 0) < self._refresh_interval:
            return
        raw = await self._adapter.fetch_balance(exchange_id)
        balances: Dict[str, Decimal] = {}
        free = raw.get("free", {})
        total = raw.get("total", {})
        for currency, _ in total.items():
            free_value = Decimal(str(free.get(currency, 0)))
            balances[currency] = free_value
        self._balances[exchange_id] = balances
        self._last_refresh[exchange_id] = now
        logger.info(
            "[BALANCE] Updated cache for %s assets=%d sample=%s",
            exchange_id.upper(),
            len(balances),
            list(balances.items())[:5],
        )

    async def force_refresh(self, exchange_id: str) -> Dict[str, Decimal]:
        async with self._lock:
            self._last_refresh[exchange_id] = 0.0
            await self._maybe_refresh(exchange_id)
            return dict(self._balances.get(exchange_id, {}))


# ---------------------------------------------------------------------------
# Instant fill response engine
# ---------------------------------------------------------------------------


class InstantFillResponseEngine:
    """Tracks active orders and reacts to fills immediately."""

    def __init__(
        self,
        adapter: ExchangeManagerAdapter,
        db_manager: DatabaseManager,
        pair_configs: Sequence[PairConfig],
        latency_warning_ms: float = 500.0,
        order_registered_cb: Optional[Callable[[ManagedOrder], None]] = None,
        order_cancelled_cb: Optional[Callable[[ManagedOrder], None]] = None,
        fill_callback: Optional[Callable[[ManagedOrder, FillEvent], None]] = None,
    ) -> None:
        self._adapter = adapter
        self._db = db_manager
        self._latency_warning_ms = latency_warning_ms
        self._order_registered_cb = order_registered_cb
        self._order_cancelled_cb = order_cancelled_cb
        self._fill_callback = fill_callback

        self._pair_lookup: Dict[Tuple[str, str], PairConfig] = {
            (cfg.exchange_id, cfg.symbol): cfg for cfg in pair_configs
        }

        self._orders: Dict[Tuple[str, str], ManagedOrder] = {}
        self._orders_by_pair: Dict[Tuple[str, str, OrderSide], ManagedOrder] = {}
        self._lock = asyncio.Lock()

        self._pending_trades: Deque[FillEvent] = deque()
        self._metrics = {
            "fills_processed": 0,
            "opposite_failures": 0,
            "latency_ms": [],
        }
        self._last_fill_ts: Optional[float] = None
        self._last_fill_by_pair: Dict[Tuple[str, str], float] = {}
        self._fill_count_by_pair: Dict[Tuple[str, str], int] = defaultdict(int)
        self._pending_by_pair: Dict[Tuple[str, str], int] = defaultdict(int)

    def get_metrics(self) -> Dict[str, float]:
        latencies = self._metrics["latency_ms"]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
        p95_latency = (
            sorted(latencies)[int(len(latencies) * 0.95)]
            if latencies
            else 0.0
        )
        return {
            "total_fills_processed": self._metrics["fills_processed"],
            "failed_opposite_failures": self._metrics["opposite_failures"],
            "average_latency_ms": avg_latency,
            "p95_latency_ms": p95_latency,
            "pending_fills": len(self._pending_trades),
            "seconds_since_last_fill":
            (time.time() - self._last_fill_ts)
            if self._last_fill_ts
            else None,
            "fills_by_pair": dict(self._fill_count_by_pair),
            "pending_by_pair": dict(self._pending_by_pair),
        }

    @property
    def last_fill_timestamp(self) -> Optional[float]:
        return self._last_fill_ts

    def last_fill_time(self, exchange_id: str, symbol: str) -> Optional[float]:
        return self._last_fill_by_pair.get((exchange_id, symbol))

    def get_active_order(
        self, exchange_id: str, symbol: str, side: OrderSide
    ) -> Optional[ManagedOrder]:
        return self._orders_by_pair.get((exchange_id, symbol, side))

    def has_active_sell_order(self, exchange_id: str, base_asset: str) -> bool:
        for order in self._orders.values():
            if order.exchange_id != exchange_id or order.side != OrderSide.SELL:
                continue
            base, _ = order.symbol.split("/")
            if base == base_asset:
                return True
        return False

    def reserved_quote(self, exchange_id: str, quote: str) -> Decimal:
        total = Decimal("0")
        for order in self._orders.values():
            if order.exchange_id != exchange_id or order.side != OrderSide.BUY:
                continue
            base, order_quote = order.symbol.split("/")
            if order_quote == quote:
                total += order.price * order.amount
        logger.info(
            "[OMS] Reserved quote %s on %s = %s",
            quote,
            exchange_id.upper(),
            total,
        )
        return total

    def reserved_base(self, exchange_id: str, base: str) -> Decimal:
        total = Decimal("0")
        for order in self._orders.values():
            if order.exchange_id != exchange_id or order.side != OrderSide.SELL:
                continue
            order_base, _ = order.symbol.split("/")
            if order_base == base:
                total += order.amount
        logger.info(
            "[OMS] Reserved base %s on %s = %s",
            base,
            exchange_id.upper(),
            total,
        )
        return total

    async def register_order(self, order: ManagedOrder) -> None:
        key = (order.exchange_id, order.order_id)
        side_key = (order.exchange_id, order.symbol, order.side)
        async with self._lock:
            self._orders[key] = order
            self._orders_by_pair[side_key] = order
        logger.info(
            "[OMS] 📥 Registered order %s %s %s %s @ %s x%s (tag=%s)",
            order.exchange_id.upper(),
            order.side.value.upper(),
            order.symbol,
            order.order_id,
            order.price,
            order.amount,
            order.tag,
        )
        if order.tag == "hedge":
            self._pending_by_pair[(order.exchange_id, order.symbol)] += 1
        if self._order_registered_cb:
            await maybe_awaitable(self._order_registered_cb(order))

    async def mark_cancelled(
        self, exchange_id: str, symbol: str, side: OrderSide
    ) -> None:
        side_key = (exchange_id, symbol, side)
        async with self._lock:
            existing = self._orders_by_pair.pop(side_key, None)
            if existing:
                self._orders.pop((exchange_id, existing.order_id), None)
        logger.info(
            "[OMS] 🗑️ Removed tracked order %s %s %s",
            exchange_id.upper(),
            symbol,
            side.value.upper(),
        )
        if existing and existing.tag == "hedge":
            self._pending_by_pair[(existing.exchange_id, existing.symbol)] = max(
                0,
                self._pending_by_pair.get((existing.exchange_id, existing.symbol), 0) - 1,
            )
        if existing and self._order_cancelled_cb:
            await maybe_awaitable(self._order_cancelled_cb(existing))

    async def get_orders_by_tag(self, tag: str) -> List[ManagedOrder]:
        async with self._lock:
            return [order for order in self._orders.values() if order.tag == tag]

    async def enqueue_fill(self, fill: FillEvent) -> None:
        async with self._lock:
            self._pending_trades.append(fill)
        logger.info(
            "[OMS] 📬 Enqueued fill %s %s %s amount=%s price=%s",
            fill.exchange_id.upper(),
            fill.symbol,
            fill.side.value.upper(),
            fill.amount,
            fill.price,
        )

    async def retry_pending_fills(self) -> None:
        """Background task to process fill queue."""
        while True:
            try:
                fill = None
                async with self._lock:
                    if self._pending_trades:
                        fill = self._pending_trades.popleft()
                if not fill:
                    await asyncio.sleep(0.2)
                    continue
                await self._process_fill(fill)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # pragma: no cover - defensive
                logger.exception("Error processing fill: %s", exc)
                await asyncio.sleep(0.5)

    async def _process_fill(self, fill: FillEvent) -> None:
        key = (fill.exchange_id, fill.order_id)
        async with self._lock:
            order = self._orders.pop(key, None)
            if order:
                self._orders_by_pair.pop(
                    (order.exchange_id, order.symbol, order.side), None
                )

        if not order:
            logger.debug(
                "[OMS] Fill received for unknown order %s on %s",
                fill.order_id,
                fill.exchange_id,
            )
            return

        latency_ms = (time.time() - order.created_at) * 1000.0
        self._metrics["fills_processed"] += 1
        self._metrics["latency_ms"].append(latency_ms)
        if latency_ms > self._latency_warning_ms:
            logger.warning(
                "[OMS] ⚠️ Opposite order latency %.1fms exceeds target %.1fms",
                latency_ms,
                self._latency_warning_ms,
            )

        logger.info(
            "[OMS] ✅ Fill processed for %s %s %s order=%s amount=%s price=%s latency=%.1fms",
            order.exchange_id.upper(),
            order.symbol,
            order.side.value.upper(),
            order.order_id,
            fill.amount,
            fill.price,
            latency_ms,
        )
        self._last_fill_ts = time.time()
        pair_key = (order.exchange_id, order.symbol)
        self._last_fill_by_pair[pair_key] = self._last_fill_ts
        self._fill_count_by_pair[pair_key] += 1
        if order.tag == "hedge":
            self._pending_by_pair[pair_key] = max(
                0,
                self._pending_by_pair.get(pair_key, 0) - 1,
            )
        if self._fill_callback:
            await maybe_awaitable(self._fill_callback(order, fill))
        await self._record_trade(order, fill)
        await self._post_opposite_order(order, fill)

    async def _record_trade(self, order: ManagedOrder, fill: FillEvent) -> None:
        try:
            trade = TradeRecord(
                symbol=order.symbol.replace("/", "-"),
                buy_exchange=order.exchange_id if order.side == OrderSide.BUY else "",
                sell_exchange=order.exchange_id
                if order.side == OrderSide.SELL
                else "",
                amount=float(fill.amount),
                buy_price=float(fill.price)
                if order.side == OrderSide.BUY
                else 0.0,
                sell_price=float(fill.price)
                if order.side == OrderSide.SELL
                else 0.0,
                profit=0.0,
                execution_time_ms=int((fill.timestamp - order.created_at) * 1000),
                slippage=0.0,
                timestamp=fill.timestamp,
                status="filled",
                strategy="instant_mm",
                risk_score=0.0,
            )
            self._db.save_trade(trade)
            logger.info(
                "[OMS] 💾 Trade recorded symbol=%s amount=%s buy_price=%s sell_price=%s",
                trade.symbol,
                trade.amount,
                trade.buy_price,
                trade.sell_price,
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug("Failed to persist trade record: %s", exc)

    async def _post_opposite_order(
        self, filled_order: ManagedOrder, fill: FillEvent
    ) -> None:
        cfg = self._pair_lookup.get((filled_order.exchange_id, filled_order.symbol))
        if not cfg:
            logger.warning(
                "[OMS] No pair config for %s on %s",
                filled_order.symbol,
                filled_order.exchange_id,
            )
            return

        side = OrderSide.SELL if filled_order.side == OrderSide.BUY else OrderSide.BUY

        if not self._adapter.is_symbol_supported(filled_order.exchange_id, filled_order.symbol):
            logger.debug(
                "[OMS] Skipping opposite order for unsupported symbol %s on %s",
                filled_order.symbol,
                filled_order.exchange_id,
            )
            return

        target_amount = fill.amount.quantize(Decimal("0.00001"))
        existing = self.get_active_order(
            filled_order.exchange_id, filled_order.symbol, side
        )
        if existing and existing.tag == "hedge":
            if existing.amount >= target_amount * Decimal("0.999"):
                logger.debug(
                    "[OMS] Existing hedge %s %s already covers %.8f",
                    filled_order.exchange_id,
                    filled_order.symbol,
                    target_amount,
                )
                return
            logger.info(
                "[OMS] 🔁 Hedge order %s %s needs resize old=%.8f new=%.8f",
                filled_order.exchange_id.upper(),
                filled_order.symbol,
                existing.amount,
                target_amount,
            )
            try:
                await self._adapter.cancel_order(
                    filled_order.exchange_id, filled_order.symbol, existing.order_id
                )
                await self.mark_cancelled(
                    filled_order.exchange_id, filled_order.symbol, side
                )
                logger.debug(
                    "[OMS] Replacing hedge for %s %s (old %.8f < new %.8f)",
                    filled_order.exchange_id,
                    filled_order.symbol,
                    existing.amount,
                    target_amount,
                )
            except Exception as exc:
                logger.debug(
                    "[OMS] Failed to cancel existing hedge %s on %s: %s",
                    existing.order_id,
                    filled_order.exchange_id,
                    exc,
                )
                return

        try:
            order_book = await self._adapter.fetch_order_book(
                filled_order.exchange_id, filled_order.symbol, depth=5
            )
        except Exception as exc:
            logger.debug(
                "[OMS] Unable to fetch order book for %s: %s",
                filled_order.symbol,
                exc,
            )
            return

        best_bid = Decimal(str(order_book["bids"][0][0])) if order_book["bids"] else fill.price
        best_ask = Decimal(str(order_book["asks"][0][0])) if order_book["asks"] else fill.price
        mid = (best_bid + best_ask) / Decimal("2")

        spread = Decimal(cfg.min_spread_bps) / Decimal("10000")
        improve = Decimal(cfg.price_improve_bps) / Decimal("10000")
        if side == OrderSide.SELL:
            price = max(mid * (Decimal("1") + spread / Decimal("2")), best_ask - mid * improve)
        else:
            price = min(mid * (Decimal("1") - spread / Decimal("2")), best_bid + mid * improve)

        price = price.quantize(Decimal("0.00001"))
        amount = target_amount

        logger.info(
            "[OMS] ➡️ Posting opposite %s for %s on %s price=%s amount=%s",
            side.value,
            filled_order.symbol,
            filled_order.exchange_id.upper(),
            price,
            amount,
        )
        try:
            response = await self._adapter.create_order(
                filled_order.exchange_id,
                filled_order.symbol,
                side,
                amount=amount,
                price=price,
                order_type="limit",
            )
            order_id = response.get("id") or response.get("order_id")
            if not order_id:
                raise ValueError("Order response missing id")
            new_order = ManagedOrder(
                exchange_id=filled_order.exchange_id,
                symbol=filled_order.symbol,
                side=side,
                order_id=str(order_id),
                price=price,
                amount=amount,
                tag="hedge",
            )
            await self.register_order(new_order)
            logger.info(
                "[OMS] ⚡ Opposite %s order posted for %s @ %s x%s",
                side.value,
                filled_order.symbol,
                price,
                amount,
            )
        except Exception as exc:
            self._metrics["opposite_failures"] += 1
            logger.error(
                "[OMS] Failed to post opposite order for %s %s: %s",
                filled_order.exchange_id,
                filled_order.symbol,
                exc,
            )


# ---------------------------------------------------------------------------
# Quote manager
# ---------------------------------------------------------------------------


class DualSideQuoteManager:
    def __init__(
        self,
        adapter: ExchangeManagerAdapter,
        response_engine: InstantFillResponseEngine,
        balance_cache: BalanceCache,
        pair_configs: Sequence[PairConfig],
        pair_cooldowns: Dict[Tuple[str, str], float],
        fee_floor_bps: Dict[str, Decimal],
    ) -> None:
        self._adapter = adapter
        self._response_engine = response_engine
        self._balance_cache = balance_cache
        self._pair_configs = list(pair_configs)
        self._last_quote_time: Dict[Tuple[str, str], float] = {}
        self._pair_cooldowns = pair_cooldowns
        self._inactivity_tighten_threshold = 600.0
        self._exchange_fee_floor_bps = fee_floor_bps
        self._stable_currencies = {"USD", "USDC", "USDT", "GUSD"}
        self._stable_aliases: Dict[str, Sequence[str]] = {
            "USD": ("USDC", "USDT", "GUSD"),
            "USDC": ("USD", "USDT"),
            "USDT": ("USD", "USDC"),
            "GUSD": ("USD",),
        }
        self._stale_quote_multiplier = 2.0
        self._ioc_slippage = Decimal("0.0015")
        self._min_conversion_chunk = Decimal("5")
        self._orphan_cancel_age_s = 90.0
        self._volatility_cache: Dict[
            Tuple[str, str], Tuple[float, Optional[float]]
        ] = {}
        self._volatility_refresh_s = 120.0

    async def ensure_quotes(self, prioritized: Optional[Sequence[PairConfig]] = None) -> None:
        configs: Sequence[PairConfig] = prioritized if prioritized is not None else self._pair_configs
        for cfg in configs:
            now = time.time()
            cooldown_until = self._pair_cooldowns.get((cfg.exchange_id, cfg.symbol))
            if cooldown_until and now < cooldown_until:
                logger.info(
                    "[QUOTE] Cooldown active for %s %s (%.1fs remaining)",
                    cfg.exchange_id.upper(),
                    cfg.symbol,
                    cooldown_until - now,
                )
                continue
            last = self._last_quote_time.get((cfg.exchange_id, cfg.symbol), 0.0)
            if now - last < cfg.max_quote_interval_s:
                logger.info(
                    "[QUOTE] Skipping %s %s (cooldown %.2fs)",
                    cfg.exchange_id.upper(),
                    cfg.symbol,
                    cfg.max_quote_interval_s - (now - last),
                )
                continue
            try:
                await self._ensure_pair(cfg)
            except Exception as exc:  # pragma: no cover - defensive
                logger.debug(
                    "[QUOTE] Skipped %s %s due to error: %s",
                    cfg.exchange_id,
                    cfg.symbol,
                    exc,
                )
            finally:
                self._last_quote_time[(cfg.exchange_id, cfg.symbol)] = time.time()

    async def _get_short_term_volatility(
        self, cfg: PairConfig, limit: int = 30
    ) -> Optional[float]:
        cache_key = (cfg.exchange_id, cfg.symbol)
        cached = self._volatility_cache.get(cache_key)
        now = time.time()
        if cached and now - cached[0] < self._volatility_refresh_s:
            return cached[1]
        try:
            candles = await self._adapter.fetch_ohlcv(
                cfg.exchange_id, cfg.symbol, timeframe="1m", limit=limit
            )
        except Exception as exc:
            logger.debug(
                "[VOL] Unable to fetch OHLCV for %s %s: %s",
                cfg.exchange_id.upper(),
                cfg.symbol,
                exc,
            )
            return cached[1] if cached else None
        closes: List[float] = [
            float(candle[4])
            for candle in candles
            if candle and len(candle) > 4 and candle[4]
        ]
        if len(closes) < 5:
            return None
        returns: List[float] = []
        for i in range(1, len(closes)):
            prev = closes[i - 1]
            curr = closes[i]
            if prev <= 0:
                continue
            returns.append((curr / prev) - 1.0)
        if len(returns) < 4:
            return None
        mean = sum(returns) / len(returns)
        variance = sum((r - mean) ** 2 for r in returns) / len(returns)
        volatility = math.sqrt(variance)
        self._volatility_cache[cache_key] = (now, volatility)
        logger.debug(
            "[VOL] %s %s volatility=%.6f (samples=%s)",
            cfg.exchange_id.upper(),
            cfg.symbol,
            volatility,
            len(returns),
        )
        return volatility

    async def _ensure_pair(self, cfg: PairConfig) -> None:
        if not self._adapter.is_symbol_supported(cfg.exchange_id, cfg.symbol):
            logger.debug(
                "[FILTER] Skipping unsupported symbol %s on %s",
                cfg.symbol,
                cfg.exchange_id,
            )
            return

        if cfg.min_volume_usd > 0:
            try:
                ticker = await self._adapter.fetch_ticker(cfg.exchange_id, cfg.symbol)
            except Exception as exc:
                logger.info(
                    "[QUOTE] Skip %s %s: failed to fetch ticker for volume check (%s)",
                    cfg.exchange_id.upper(),
                    cfg.symbol,
                    exc,
                )
                return
            quote_volume = self._extract_quote_volume_usd(ticker, cfg.symbol)
            if quote_volume is None:
                logger.debug(
                    "[QUOTE] Skip %s %s: unable to determine quote volume from ticker %s",
                    cfg.exchange_id.upper(),
                    cfg.symbol,
                    ticker,
                )
                return
            if quote_volume < cfg.min_volume_usd:
                logger.info(
                    "[QUOTE] Skip %s %s: 24h volume %s < min_volume_usd %s",
                    cfg.exchange_id.upper(),
                    cfg.symbol,
                    quote_volume,
                    cfg.min_volume_usd,
                )
                return

        try:
            order_book = await self._adapter.fetch_order_book(
                cfg.exchange_id, cfg.symbol, depth=5
            )
        except Exception:
            return
        if not order_book["bids"] or not order_book["asks"]:
            logger.info(
                "[QUOTE] Skip %s %s: empty order book bids=%s asks=%s",
                cfg.exchange_id.upper(),
                cfg.symbol,
                order_book["bids"],
                order_book["asks"],
            )
            return

        best_bid = Decimal(str(order_book["bids"][0][0]))
        best_ask = Decimal(str(order_book["asks"][0][0]))
        bid_depth = sum(Decimal(str(entry[1])) * Decimal(str(entry[0])) for entry in order_book["bids"][:3])
        ask_depth = sum(Decimal(str(entry[1])) * Decimal(str(entry[0])) for entry in order_book["asks"][:3])
        depth_capacity = min(bid_depth, ask_depth)

        logger.info(
            "[QUOTE] %s %s best_bid=%s best_ask=%s bid_depth=%.2f ask_depth=%.2f",
            cfg.exchange_id.upper(),
            cfg.symbol,
            best_bid,
            best_ask,
            bid_depth,
            ask_depth,
        )

        if bid_depth < cfg.min_depth_usd or ask_depth < cfg.min_depth_usd:
            logger.debug(
                "[QUOTE] Depth too low for %s (%s/%s)",
                cfg.symbol,
                bid_depth,
                ask_depth,
            )
            return

        mid = (best_bid + best_ask) / Decimal("2")
        last_fill_time = self._response_engine.last_fill_time(cfg.exchange_id, cfg.symbol)
        last_fill_age = None
        if last_fill_time:
            last_fill_age = time.time() - last_fill_time
        adjusted_spread_bps = Decimal(cfg.min_spread_bps)
        adjusted_price_improve_bps = Decimal(cfg.price_improve_bps)
        if last_fill_age and last_fill_age > self._inactivity_tighten_threshold:
            adjusted_spread_bps = max(adjusted_spread_bps - Decimal("5"), Decimal("5"))
            adjusted_price_improve_bps = max(adjusted_price_improve_bps - Decimal("1"), Decimal("1"))
            logger.info(
                "[QUOTE] Tightening spread for %s %s due to inactivity %.1fs",
                cfg.exchange_id.upper(),
                cfg.symbol,
                last_fill_age,
            )
        fee_floor_bps = max(
            Decimal(cfg.fee_floor_bps),
            self._exchange_fee_floor_bps.get(cfg.exchange_id, Decimal("0")),
        )
        if adjusted_spread_bps < fee_floor_bps:
            logger.info(
                "[QUOTE] Adjusting %s %s spread floor from %s bps to fee floor %s bps",
                cfg.exchange_id.upper(),
                cfg.symbol,
                adjusted_spread_bps,
                fee_floor_bps,
            )
            adjusted_spread_bps = fee_floor_bps
        volatility = await self._get_short_term_volatility(cfg)
        volatility_bps: Optional[Decimal] = None
        if volatility is not None:
            volatility_bps = (Decimal(str(volatility)) * Decimal("10000")).quantize(
                Decimal("0.01")
            )
            vol_bump = (volatility_bps * Decimal("0.25")).quantize(Decimal("0.01"))
            vol_bump = min(vol_bump, Decimal("150"))
            adjusted_spread_bps += vol_bump
            if volatility > 0.015:
                adjusted_price_improve_bps = max(
                    adjusted_price_improve_bps - Decimal("1"), Decimal("1")
                )
            elif volatility < 0.004:
                adjusted_price_improve_bps += Decimal("1")
            logger.debug(
                "[QUOTE] Volatility adjust %s %s vol_bps=%s bump=%s price_improve=%s",
                cfg.exchange_id.upper(),
                cfg.symbol,
                volatility_bps,
                vol_bump,
                adjusted_price_improve_bps,
            )
        min_spread = adjusted_spread_bps / Decimal("10000")
        spread = max((best_ask - best_bid) / mid, min_spread)
        price_improve = adjusted_price_improve_bps / Decimal("10000")
        buy_price = mid * (Decimal("1") - spread / Decimal("2"))
        sell_price = mid * (Decimal("1") + spread / Decimal("2"))
        if price_improve > 0:
            buy_price -= mid * price_improve
            sell_price += mid * price_improve
        buy_price = buy_price.quantize(Decimal("0.00001"))
        sell_price = sell_price.quantize(Decimal("0.00001"))

        base, quote = cfg.symbol.split("/")
        quote_balance = await self._balance_cache.get_balance(cfg.exchange_id, quote)
        base_balance = await self._balance_cache.get_balance(cfg.exchange_id, base)

        total_stable_equity = await self._balance_cache.get_equity(
            cfg.exchange_id, self._stable_currencies
        )

        cancelled_buy = await self._cancel_orphan_orders(cfg, OrderSide.BUY)
        cancelled_sell = await self._cancel_orphan_orders(cfg, OrderSide.SELL)
        if cancelled_buy or cancelled_sell:
            await self._balance_cache.force_refresh(cfg.exchange_id)
            quote_balance = await self._balance_cache.get_balance(cfg.exchange_id, quote)
            base_balance = await self._balance_cache.get_balance(cfg.exchange_id, base)

        quote_reserved = self._response_engine.reserved_quote(cfg.exchange_id, quote)
        base_reserved = self._response_engine.reserved_base(cfg.exchange_id, base)

        usable_quote = max(Decimal("0"), quote_balance - quote_reserved)
        usable_base = max(Decimal("0"), base_balance - base_reserved)

        effective_min_notional = Decimal(cfg.min_notional_usd)
        if total_stable_equity > Decimal("0"):
            scaled_floor = (total_stable_equity * Decimal("0.25")).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            scaled_floor = max(Decimal("5"), scaled_floor)
            effective_min_notional = min(effective_min_notional, scaled_floor)
        effective_min_notional = max(Decimal("5"), effective_min_notional)

        target_order_value = Decimal(cfg.order_size_usd)
        if total_stable_equity > Decimal("0"):
            budget_cap = (total_stable_equity * Decimal("0.4")).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            if budget_cap > Decimal("0"):
                target_order_value = min(target_order_value, budget_cap)
        if usable_quote > Decimal("0"):
            quote_cap = (usable_quote * Decimal("0.8")).quantize(
                Decimal("0.01"), rounding=ROUND_DOWN
            )
            if quote_cap > Decimal("0"):
                target_order_value = min(target_order_value, quote_cap)

        target_order_value = max(effective_min_notional, target_order_value)
        dynamic_multiplier = Decimal("1")

        logger.debug(
            "[QUOTE] %s %s totals stable=%s effective_min=%s target_value=%s usable_quote=%s",
            cfg.exchange_id.upper(),
            cfg.symbol,
            total_stable_equity,
            effective_min_notional,
            target_order_value,
            usable_quote,
        )

        if usable_quote < Decimal(cfg.min_notional_usd):
            cancelled = await self._cancel_orphan_orders(cfg, OrderSide.BUY)
            if cancelled:
                await self._balance_cache.force_refresh(cfg.exchange_id)
                quote_balance = await self._balance_cache.get_balance(cfg.exchange_id, quote)
                quote_reserved = self._response_engine.reserved_quote(cfg.exchange_id, quote)
                usable_quote = max(Decimal("0"), quote_balance - quote_reserved)

        min_base_required = Decimal(cfg.min_notional_usd) / max(Decimal("1"), sell_price)
        if usable_base < min_base_required:
            cancelled = await self._cancel_orphan_orders(cfg, OrderSide.SELL)
            if cancelled:
                await self._balance_cache.force_refresh(cfg.exchange_id)
                base_balance = await self._balance_cache.get_balance(cfg.exchange_id, base)
                base_reserved = self._response_engine.reserved_base(cfg.exchange_id, base)
                usable_base = max(Decimal("0"), base_balance - base_reserved)

        convertible_sources = self._stable_aliases.get(quote, ())
        if (
            convertible_sources
            and usable_quote < Decimal(cfg.min_notional_usd)
        ):
            for alt_currency in convertible_sources:
                if alt_currency == quote:
                    continue
                alt_balance = await self._balance_cache.get_balance(cfg.exchange_id, alt_currency)
                if alt_balance <= self._min_conversion_chunk:
                    continue
                alt_reserved = self._response_engine.reserved_quote(cfg.exchange_id, alt_currency)
                usable_alt = max(Decimal("0"), alt_balance - alt_reserved)
                if usable_alt <= self._min_conversion_chunk:
                    continue
                required = (
                    max(Decimal(cfg.order_size_usd), Decimal(cfg.min_notional_usd))
                    - usable_quote
                )
                if required <= Decimal("0"):
                    break
                convert_amount = min(
                    usable_alt,
                    (required * Decimal("1.2")).quantize(Decimal("0.01"), rounding=ROUND_DOWN),
                )
                if convert_amount < self._min_conversion_chunk:
                    continue
                logger.info(
                    "[QUOTE] Converting %s -> %s amount=%s to fund %s %s",
                    alt_currency,
                    quote,
                    convert_amount,
                    cfg.exchange_id.upper(),
                    cfg.symbol,
                )
                try:
                    success = await self._adapter.convert_currency(
                        cfg.exchange_id,
                        alt_currency,
                        quote,
                        convert_amount,
                    )
                except Exception as exc:  # pragma: no cover - defensive
                    logger.warning(
                        "[QUOTE] Conversion %s -> %s failed on %s: %s",
                        alt_currency,
                        quote,
                        cfg.exchange_id.upper(),
                        exc,
                    )
                    success = False
                if success:
                    logger.info(
                        "[QUOTE] Conversion %s -> %s succeeded on %s amount=%s",
                        alt_currency,
                        quote,
                        cfg.exchange_id.upper(),
                        convert_amount,
                    )
                    await self._balance_cache.force_refresh(cfg.exchange_id)
                    quote_balance = await self._balance_cache.get_balance(cfg.exchange_id, quote)
                    quote_reserved = self._response_engine.reserved_quote(cfg.exchange_id, quote)
                    usable_quote = max(Decimal("0"), quote_balance - quote_reserved)
                    break

        if volatility is not None:
            if volatility > 0.015:
                dynamic_multiplier *= Decimal("0.6")
            elif volatility > 0.01:
                dynamic_multiplier *= Decimal("0.8")
            elif volatility < 0.003:
                dynamic_multiplier *= Decimal("1.15")
        if depth_capacity > Decimal("0"):
            depth_ratio = depth_capacity / max(target_order_value, Decimal("1"))
        else:
            depth_ratio = Decimal("0")
        if depth_ratio < Decimal("1.5"):
            dynamic_multiplier *= Decimal("0.6")
        elif depth_ratio < Decimal("2.5"):
            dynamic_multiplier *= Decimal("0.85")
        elif depth_ratio > Decimal("6"):
            dynamic_multiplier *= Decimal("1.6")
        elif depth_ratio > Decimal("3.5"):
            dynamic_multiplier *= Decimal("1.25")
        if usable_quote > target_order_value * Decimal("4"):
            dynamic_multiplier *= Decimal("1.3")
        elif usable_quote < Decimal(cfg.min_notional_usd):
            dynamic_multiplier *= Decimal("0.7")
        dynamic_multiplier = min(max(dynamic_multiplier, Decimal("0.35")), Decimal("2.5"))
        logger.debug(
            "[QUOTE] %s %s dynamic multiplier=%s depth_ratio=%s volatility_bps=%s usable_quote=%s",
            cfg.exchange_id.upper(),
            cfg.symbol,
            dynamic_multiplier,
            depth_ratio.quantize(Decimal("0.01")) if depth_ratio > 0 else depth_ratio,
            volatility_bps,
            usable_quote,
        )
        order_value = target_order_value * dynamic_multiplier
        order_value = max(order_value, effective_min_notional)
        order_value = min(order_value, usable_quote) if usable_quote > 0 else order_value
        buy_amount = (order_value / buy_price).quantize(Decimal("0.00001"))
        sell_amount = (order_value / sell_price).quantize(Decimal("0.00001"))

        if usable_base > Decimal("0") and sell_amount > Decimal("0") and usable_base > sell_amount * Decimal("3"):
            sell_amount = min(
                (usable_base * Decimal("0.5")).quantize(Decimal("0.00001")),
                (sell_amount * Decimal("2")).quantize(Decimal("0.00001")),
            )

        if bid_depth < order_value * Decimal("2") or ask_depth < order_value * Decimal("2"):
            logger.info(
                "[QUOTE] Skipping %s %s depth insufficient for order_value=%s",
                cfg.exchange_id.upper(),
                cfg.symbol,
                order_value,
            )
            return

        max_buy_amount = (
            usable_quote / (buy_price * Decimal("1.01"))
        ).quantize(Decimal("0.00001")) if buy_price > 0 else Decimal("0")
        buy_amount = min(buy_amount, max_buy_amount)

        sell_amount = min(sell_amount, usable_base.quantize(Decimal("0.00001")))

        now_ts = time.time()
        stale_threshold = max(cfg.max_quote_interval_s * self._stale_quote_multiplier, 10.0)
        escalate_buy = False
        escalate_sell = False
        buy_params: Optional[Dict[str, Any]] = None
        sell_params: Optional[Dict[str, Any]] = None

        existing_buy = self._response_engine.get_active_order(
            cfg.exchange_id, cfg.symbol, OrderSide.BUY
        )
        if existing_buy:
            age = now_ts - existing_buy.created_at
            if age > stale_threshold:
                escalate_buy = True
                buy_amount = existing_buy.amount
                buy_price = (best_ask * (Decimal("1") + self._ioc_slippage)).quantize(
                    Decimal("0.00001")
                )
                if cfg.exchange_id == "gemini":
                    buy_params = {"options": ["immediate-or-cancel"]}
                elif cfg.exchange_id == "coinbase":
                    buy_params = {"time_in_force": "IOC"}
                logger.info(
                    "[QUOTE] Escalating stale BUY for %s %s age=%.2fs new_price=%s amount=%s",
                    cfg.exchange_id.upper(),
                    cfg.symbol,
                    age,
                    buy_price,
                    buy_amount,
                )

        existing_sell = self._response_engine.get_active_order(
            cfg.exchange_id, cfg.symbol, OrderSide.SELL
        )
        if existing_sell:
            age = now_ts - existing_sell.created_at
            if age > stale_threshold:
                escalate_sell = True
                sell_amount = existing_sell.amount
                sell_price = (best_bid * (Decimal("1") - self._ioc_slippage)).quantize(
                    Decimal("0.00001")
                )
                if cfg.exchange_id == "gemini":
                    sell_params = {"options": ["immediate-or-cancel"]}
                elif cfg.exchange_id == "coinbase":
                    sell_params = {"time_in_force": "IOC"}
                logger.info(
                    "[QUOTE] Escalating stale SELL for %s %s age=%.2fs new_price=%s amount=%s",
                    cfg.exchange_id.upper(),
                    cfg.symbol,
                    age,
                    sell_price,
                    sell_amount,
                )

        need_buy = buy_amount > Decimal("0") and (buy_amount * buy_price) >= cfg.min_notional_usd
        need_sell = sell_amount > Decimal("0") and (sell_amount * sell_price) >= cfg.min_notional_usd

        if escalate_buy:
            need_buy = True
        if escalate_sell:
            need_sell = True

        logger.info(
            "[QUOTE] Computed orders %s %s buy_amount=%s buy_price=%s sell_amount=%s sell_price=%s need_buy=%s need_sell=%s",
            cfg.exchange_id.upper(),
            cfg.symbol,
            buy_amount,
            buy_price,
            sell_amount,
            sell_price,
            need_buy,
            need_sell,
        )
        if not need_buy:
            logger.info(
                "[QUOTE] BUY skipped for %s %s reason=%s",
                cfg.exchange_id.upper(),
                cfg.symbol,
                "notional below minimum" if buy_amount * buy_price < cfg.min_notional_usd else "insufficient balance",
            )
        if not need_sell:
            logger.info(
                "[QUOTE] SELL skipped for %s %s reason=%s",
                cfg.exchange_id.upper(),
                cfg.symbol,
                "notional below minimum" if sell_amount * sell_price < cfg.min_notional_usd else "insufficient inventory",
            )

        await self._sync_side(
            cfg,
            OrderSide.BUY,
            buy_amount,
            buy_price,
            need_buy,
            escalate_buy,
            buy_params,
        )
        await self._sync_side(
            cfg,
            OrderSide.SELL,
            sell_amount,
            sell_price,
            need_sell,
            escalate_sell,
            sell_params,
        )

    async def _cancel_orphan_orders(self, cfg: PairConfig, side: OrderSide) -> bool:
        try:
            open_orders = await self._adapter.fetch_open_orders(cfg.exchange_id, cfg.symbol)
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug(
                "[QUOTE] Unable to fetch open orders for %s %s: %s",
                cfg.exchange_id.upper(),
                cfg.symbol,
                exc,
            )
            return False

        tracked = self._response_engine.get_active_order(cfg.exchange_id, cfg.symbol, side)
        tracked_client_id = None
        tracked_order_id = None
        tracked_age = None
        if tracked:
            tracked_order_id = tracked.order_id
            tracked_client_id = getattr(tracked, "client_order_id", None)
            tracked_age = time.time() - tracked.created_at

        cancelled = False

        for order in open_orders:
            raw_side = str(
                order.get("side")
                or order.get("info", {}).get("side", "")
            ).lower()
            if raw_side != side.value:
                continue
            order_id = str(
                order.get("id")
                or order.get("order_id")
                or order.get("clientOrderId")
                or order.get("client_order_id")
                or ""
            )
            if not order_id:
                continue

            info = order.get("info", {}) or {}
            client_id = str(
                order.get("clientOrderId")
                or order.get("client_order_id")
                or info.get("clientOrderId")
                or info.get("client_order_id")
                or ""
            ) or None

            should_cancel = True

            if tracked_order_id and order_id == tracked_order_id:
                if tracked_age is None or tracked_age <= self._orphan_cancel_age_s:
                    should_cancel = False
                else:
                    logger.info(
                        "[QUOTE] Tracked order %s %s age=%.2fs exceeds stale threshold %.0fs; cancelling.",
                        cfg.exchange_id.upper(),
                        order_id,
                        tracked_age,
                        self._orphan_cancel_age_s,
                    )
            if should_cancel and tracked_client_id and client_id == tracked_client_id:
                if tracked_age is None or tracked_age <= self._orphan_cancel_age_s:
                    should_cancel = False
                else:
                    logger.info(
                        "[QUOTE] Tracked client order %s age=%.2fs exceeds stale threshold %.0fs; cancelling.",
                        client_id,
                        tracked_age,
                        self._orphan_cancel_age_s,
                    )
            if not should_cancel:
                continue

            symbol = order.get("symbol") or info.get("symbol") or cfg.symbol
            try:
                amount = Decimal(str(order.get("remaining") or order.get("remaining_amount") or order.get("amount") or info.get("remaining_amount") or 0))
            except Exception:
                amount = Decimal("0")
            try:
                price = Decimal(str(order.get("price") or info.get("price") or 0))
            except Exception:
                price = Decimal("0")

            logger.info(
                "[QUOTE] Cancelling orphan %s order %s symbol=%s amount=%s price=%s tracked_order=%s tracked_client=%s",
                side.value.upper(),
                order_id,
                symbol,
                amount,
                price,
                tracked_order_id,
                tracked_client_id,
            )
            try:
                await self._adapter.cancel_order(cfg.exchange_id, order_id, symbol)
                await self._response_engine.mark_cancelled(cfg.exchange_id, symbol, side)
                cancelled = True
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning(
                    "[QUOTE] Failed to cancel orphan %s order %s on %s %s: %s",
                    side.value.upper(),
                    order_id,
                    cfg.exchange_id.upper(),
                    symbol,
                    exc,
                )

        if cancelled:
            logger.info(
                "[QUOTE] Completed orphan cancellation sweep for %s %s side=%s",
                cfg.exchange_id.upper(),
                cfg.symbol,
                side.value.upper(),
            )

        return cancelled

    @staticmethod
    def _extract_quote_volume_usd(ticker: Dict[str, Any], symbol: str) -> Optional[Decimal]:
        keys = (
            "quoteVolume",
            "quote_volume",
            "quoteVolume24h",
            "info.quoteVolume",
            "info.quote_volume",
        )
        for key in keys:
            ref = ticker
            for part in key.split("."):
                if isinstance(ref, dict) and part in ref:
                    ref = ref[part]
                else:
                    ref = None
                    break
            if ref is not None:
                try:
                    volume = Decimal(str(ref))
                    if volume >= Decimal("0"):
                        return volume
                except Exception:
                    continue
        base_volume = ticker.get("baseVolume") or ticker.get("base_volume")
        last_price = (
            ticker.get("last")
            or ticker.get("close")
            or ticker.get("average")
            or ticker.get("ask")
            or ticker.get("bid")
        )
        if base_volume is not None and last_price is not None:
            try:
                base = Decimal(str(base_volume))
                price = Decimal(str(last_price))
                if base >= Decimal("0") and price > Decimal("0"):
                    return base * price
            except Exception:
                return None
        return None

    async def _sync_side(
        self,
        cfg: PairConfig,
        side: OrderSide,
        amount: Decimal,
        price: Decimal,
        allowed: bool,
        escalate: bool = False,
        order_params: Optional[Dict[str, Any]] = None,
    ) -> None:
        existing = self._response_engine.get_active_order(
            cfg.exchange_id, cfg.symbol, side
        )
        if existing and existing.tag == "hedge":
            logger.debug(
                "[QUOTE] Skipping %s %s - hedge order active",
                cfg.exchange_id.upper(),
                cfg.symbol,
            )
            return
        if not allowed:
            logger.info(
                "[QUOTE] %s %s side=%s not allowed (amount=%s price=%s)",
                cfg.exchange_id.upper(),
                cfg.symbol,
                side.value,
                amount,
                price,
            )
            if existing:
                await self._adapter.cancel_order(
                    cfg.exchange_id, cfg.symbol, existing.order_id
                )
                await self._response_engine.mark_cancelled(
                    cfg.exchange_id, cfg.symbol, side
                )
            return

        if (
            existing
            and abs(existing.price - price) / price < Decimal("0.0015")
            and abs(existing.amount - amount) / amount < Decimal("0.1")
        ):
            if escalate:
                logger.info(
                    "[QUOTE] Escalation requested but existing order %s still within tolerance; cancelling to replace.",
                    existing.order_id,
                )
            else:
                logger.info(
                    "[QUOTE] %s %s reusing existing order %s",
                    cfg.exchange_id.upper(),
                    cfg.symbol,
                    existing.order_id,
                )
                return

        if existing:
            logger.info(
                "[QUOTE] %s %s cancelling existing order %s to replace",
                cfg.exchange_id.upper(),
                cfg.symbol,
                existing.order_id,
            )
            await self._adapter.cancel_order(
                cfg.exchange_id, cfg.symbol, existing.order_id
            )
            await self._response_engine.mark_cancelled(
                cfg.exchange_id, cfg.symbol, side
            )
            # refresh balances after cancellation to avoid stale locked funds
            await self._balance_cache.get_balances(cfg.exchange_id)

        logger.info(
            "[QUOTE] %s %s creating order side=%s amount=%s price=%s",
            cfg.exchange_id.upper(),
            cfg.symbol,
            side.value,
            amount,
            price,
        )
        response = await self._adapter.create_order(
            cfg.exchange_id,
            cfg.symbol,
            side,
            amount=amount,
            price=price,
            order_type="limit",
            params=order_params,
        )
        order_id = response.get("id") or response.get("order_id")
        if not order_id:
            raise ValueError("Order response missing id")
        managed = ManagedOrder(
            exchange_id=cfg.exchange_id,
            symbol=cfg.symbol,
            side=side,
            order_id=str(order_id),
            price=price,
            amount=amount,
            tag="quote",
        )
        await self._response_engine.register_order(managed)
        logger.info(
            "[QUOTE] %s %s %s @ %s x%s",
            cfg.exchange_id.upper(),
            side.value.upper(),
            cfg.symbol,
            price,
            amount,
        )


# ---------------------------------------------------------------------------
# Fill monitor (REST polling)
# ---------------------------------------------------------------------------


class WebSocketFillMonitor:
    """REST-based fill monitor that mimics WebSocket behaviour."""

    def __init__(
        self,
        adapter: ExchangeManagerAdapter,
        response_engine: InstantFillResponseEngine,
        exchange_id: str,
        poll_interval: float = 1.5,
        jitter: float = 0.25,
    ) -> None:
        self._adapter = adapter
        self._response_engine = response_engine
        self._exchange_id = exchange_id
        self._poll_interval = poll_interval
        self._jitter = max(0.0, min(jitter, 1.0))
        self._symbols: List[str] = []
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._last_trade_ts: Optional[int] = None

    async def start(self, symbols: Iterable[str]) -> None:
        self._symbols = list(symbols)
        if not self._symbols:
            return
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _run(self) -> None:
        while self._running:
            try:
                await self._poll_once()
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # pragma: no cover - defensive
                logger.debug("[WS] Poll error for %s: %s", self._exchange_id, exc)
            await asyncio.sleep(self._next_sleep_interval())

    def _next_sleep_interval(self) -> float:
        if self._jitter <= 0:
            return self._poll_interval
        low = max(0.05, self._poll_interval * (1.0 - self._jitter))
        high = self._poll_interval * (1.0 + self._jitter)
        return random.uniform(low, high)

    async def _poll_once(self) -> None:
        for symbol in self._symbols:
            logger.info(
                "[WS] Polling trades for %s %s since=%s",
                self._exchange_id.upper(),
                symbol,
                self._last_trade_ts,
            )
            trades = await self._adapter.fetch_trades(
                self._exchange_id,
                symbol,
                since=self._last_trade_ts,
            )
            if trades:
                self._last_trade_ts = max(t.get("timestamp", 0) for t in trades)
            logger.info(
                "[WS] %s %s fetched %d trades",
                self._exchange_id.upper(),
                symbol,
                len(trades or []),
            )

            for trade in trades or []:
                order_id = str(trade.get("order"))
                if not order_id:
                    continue
                amount = Decimal(str(trade.get("amount", "0")))
                price = Decimal(str(trade.get("price", "0")))
                raw_symbol = trade.get("symbol") or trade.get("info", {}).get("symbol", "") or symbol
                symbol_norm = self._normalise_symbol(raw_symbol)
                if not symbol_norm:
                    continue
                side_str = str(trade.get("side", "buy")).lower()
                if side_str not in (OrderSide.BUY.value, OrderSide.SELL.value):
                    side_str = OrderSide.BUY.value
                fill = FillEvent(
                    exchange_id=self._exchange_id,
                    symbol=symbol_norm,
                    side=OrderSide(side_str),
                    price=price,
                    amount=amount,
                    order_id=order_id,
                    timestamp=trade.get("timestamp", time.time()) / 1000.0,
                )
                await self._response_engine.enqueue_fill(fill)

        # Detect cancelled orders by comparing tracked vs open
        open_orders: List[Dict] = []
        for symbol in self._symbols:
            try:
                symbol_orders = await self._adapter.fetch_open_orders(self._exchange_id, symbol)
                logger.info(
                    "[WS] %s %s open orders fetched=%d",
                    self._exchange_id.upper(),
                    symbol,
                    len(symbol_orders),
                )
                open_orders.extend(symbol_orders)
            except Exception as exc:
                logger.debug("[WS] Open order poll failed for %s %s: %s", self._exchange_id, symbol, exc)
                continue
        open_ids = {str(order.get("id")) for order in open_orders}
        tracked: List[ManagedOrder] = []
        for symbol in self._symbols:
            for side in (OrderSide.BUY, OrderSide.SELL):
                order = self._response_engine.get_active_order(
                    self._exchange_id, symbol, side
                )
                if order:
                    tracked.append(order)
        for order in tracked:
            if not order:
                continue
            if order.order_id not in open_ids:
                # Treat as filled without trade info
                logger.info(
                    "[WS] Detected closed order %s %s %s assumed filled",
                    order.exchange_id.upper(),
                    order.symbol,
                    order.order_id,
                )
                fill = FillEvent(
                    exchange_id=self._exchange_id,
                    symbol=order.symbol,
                    side=order.side,
                    price=order.price,
                    amount=order.amount,
                    order_id=order.order_id,
                    timestamp=time.time(),
                )
                await self._response_engine.enqueue_fill(fill)

    @staticmethod
    def _normalise_symbol(raw_symbol: str) -> str:
        if not raw_symbol:
            return ""
        if "/" in raw_symbol:
            return raw_symbol
        # Insert slash before quote if possible (assume last 3 or 4 chars)
        if raw_symbol.endswith(("USD", "USDT", "USDC", "GUSD")):
            quote = raw_symbol[-3:] if raw_symbol.endswith("USD") else raw_symbol[-4:]
            base = raw_symbol[: -len(quote)]
            return f"{base}/{quote}"
        return raw_symbol


# ---------------------------------------------------------------------------
# Market maker orchestrator
# ---------------------------------------------------------------------------


class InstantFillMarketMaker:
    def __init__(
        self,
        adapter: ExchangeManagerAdapter,
        db_manager: DatabaseManager,
        pair_configs: Sequence[PairConfig],
    ) -> None:
        self._adapter = adapter
        self._db = db_manager
        self._pair_configs = [
            cfg
            for cfg in pair_configs
            if cfg.exchange_id in adapter.available_exchanges()
        ]
        self._pair_index: Dict[str, Dict[str, List[PairConfig]]] = {}
        self._inventory_check_interval = 2.0
        self._inventory_threshold = Decimal("0.00001")
        self._dust_threshold = Decimal("10.00")
        self._balance_cache = BalanceCache(adapter)
        self._pair_cooldowns: Dict[Tuple[str, str], float] = {}
        self._hedge_attempts: Dict[Tuple[str, str], int] = {}
        self._position_tracker: Dict[Tuple[str, str], List[Tuple[Decimal, Decimal]]] = defaultdict(list)
        self._realized_pnl: Decimal = Decimal("0")
        self._realized_volume: Decimal = Decimal("0")
        self._trade_count: int = 0
        self._wins: int = 0
        self._losses: int = 0
        self._break_even: int = 0
        self._fee_floor_bps: Dict[str, Decimal] = {
            "coinbase": Decimal("80"),
            "gemini": Decimal("80"),
        }
        self._pair_stats: Dict[Tuple[str, str], Dict[str, Any]] = {}
        self._max_active_pairs: int = 12
        self._last_rank_snapshot: List[Dict[str, Any]] = []
        minimum_notional = Decimal("10.00")
        for cfg in self._pair_configs:
            if cfg.order_size_usd < minimum_notional:
                logger.info(
                    "[CONFIG] Raising order_size_usd for %s %s from %s to %s",
                    cfg.exchange_id.upper(),
                    cfg.symbol,
                    cfg.order_size_usd,
                    minimum_notional,
                )
                cfg.order_size_usd = minimum_notional
            if cfg.min_notional_usd < minimum_notional:
                logger.info(
                    "[CONFIG] Raising min_notional_usd for %s %s from %s to %s",
                    cfg.exchange_id.upper(),
                    cfg.symbol,
                    cfg.min_notional_usd,
                    minimum_notional,
                )
                cfg.min_notional_usd = minimum_notional
            fee_floor = self._fee_floor_bps.get(cfg.exchange_id, Decimal("0"))
            if Decimal(cfg.fee_floor_bps) < fee_floor:
                logger.info(
                    "[CONFIG] Setting fee_floor_bps for %s %s to %s (was %s)",
                    cfg.exchange_id.upper(),
                    cfg.symbol,
                    fee_floor,
                    cfg.fee_floor_bps,
                )
                cfg.fee_floor_bps = int(fee_floor)
        self._fill_engine = InstantFillResponseEngine(
            adapter,
            db_manager,
            self._pair_configs,
            order_registered_cb=self._on_order_registered,
            order_cancelled_cb=self._on_order_cancelled,
            fill_callback=self._on_fill,
        )
        self._quote_manager = DualSideQuoteManager(
            adapter,
            self._fill_engine,
            self._balance_cache,
            self._pair_configs,
            self._pair_cooldowns,
            self._fee_floor_bps,
        )
        self._monitors: Dict[str, WebSocketFillMonitor] = {}
        self._tasks: List[asyncio.Task] = []
        self._running = False
        self._last_inactivity_warning: float = 0.0
        self._hedge_refresh_interval = 5.0
        self._hedge_max_age = 10.0
        self._metrics_interval = 300.0
        self._rebuild_pair_maps()

    def _get_pair_stats(self, pair_key: Tuple[str, str]) -> Dict[str, Any]:
        stats = self._pair_stats.get(pair_key)
        if stats is None:
            stats = {
                "wins": 0,
                "losses": 0,
                "break_even": 0,
                "trade_count": 0,
                "pnl": Decimal("0"),
                "volume": Decimal("0"),
                "avg_edge_bps": Decimal("0"),
                "last_fill_ts": None,
                "loss_streak": 0,
            }
            self._pair_stats[pair_key] = stats
        return stats

    def _select_active_pairs(self) -> List[PairConfig]:
        metrics = self._fill_engine.get_metrics()
        pending_raw = metrics.get("pending_by_pair", {})
        pending_by_pair: Dict[Tuple[str, str], int] = {}
        for key, value in pending_raw.items():
            if isinstance(key, tuple) and len(key) == 2:
                pending_by_pair[(key[0], key[1])] = value
            elif isinstance(key, str) and "|" in key:
                exchange_id, symbol = key.split("|", 1)
                pending_by_pair[(exchange_id, symbol)] = value
        now = time.time()
        ranked: List[Tuple[PairConfig, float]] = []
        snapshot: List[Dict[str, Any]] = []

        for cfg in self._pair_configs:
            pair_key = (cfg.exchange_id, cfg.symbol)
            stats = self._pair_stats.get(pair_key)
            trades = stats["trade_count"] if stats else 0
            wins = stats["wins"] if stats else 0
            losses = stats["losses"] if stats else 0
            loss_streak = stats["loss_streak"] if stats else 0
            avg_edge = float(stats["avg_edge_bps"]) if stats else 0.0
            last_fill_ts = stats["last_fill_ts"] if stats else None
            last_fill_age = (now - last_fill_ts) if last_fill_ts else None
            pending = pending_by_pair.get(pair_key, 0)

            if trades > 0:
                win_rate = wins / trades
            else:
                win_rate = 0.55  # optimistic prior for new pairs

            base_score = 0.0 if trades > 0 else 15.0
            score = base_score
            score += avg_edge * 0.6
            score += (win_rate - 0.5) * 200.0
            if last_fill_age is not None:
                score -= min(last_fill_age / 180.0, 20.0)
            score -= loss_streak * 15.0
            if pending:
                score -= min(pending * 8.0, 24.0)

            ranked.append((cfg, score))
            snapshot.append(
                {
                    "exchange": cfg.exchange_id,
                    "symbol": cfg.symbol,
                    "score": round(score, 2),
                    "win_rate_pct": round(win_rate * 100.0, 2),
                    "avg_edge_bps": round(avg_edge, 2),
                    "loss_streak": loss_streak,
                    "trades": trades,
                    "pending": pending,
                    "last_fill_age_s": round(last_fill_age, 1) if last_fill_age is not None else None,
                }
            )

        ranked.sort(key=lambda item: item[1], reverse=True)
        snapshot.sort(key=lambda item: item["score"], reverse=True)
        self._last_rank_snapshot = snapshot[:20]

        active_count = min(self._max_active_pairs, len(ranked))
        if active_count == 0:
            return list(self._pair_configs)
        return [cfg for cfg, _ in ranked[:active_count]]

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        await self._startup_cleanup()
        symbols_by_exchange: Dict[str, List[str]] = defaultdict(list)
        for cfg in self._pair_configs:
            symbols_by_exchange[cfg.exchange_id].append(cfg.symbol)

        for exchange_id, symbols in symbols_by_exchange.items():
            poll_interval = 0.5 if exchange_id == "gemini" else 1.0
            jitter = 0.35 if exchange_id == "gemini" else 0.2
            monitor = WebSocketFillMonitor(
                self._adapter,
                self._fill_engine,
                exchange_id,
                poll_interval=poll_interval,
                jitter=jitter,
            )
            await monitor.start(symbols)
            self._monitors[exchange_id] = monitor

        self._tasks.append(asyncio.create_task(self._fill_engine.retry_pending_fills()))
        self._tasks.append(asyncio.create_task(self._quote_loop()))
        self._tasks.append(asyncio.create_task(self._balance_refresh_loop()))
        self._tasks.append(asyncio.create_task(self._inventory_guard_loop()))
        self._tasks.append(asyncio.create_task(self._hedge_refresh_loop()))
        self._tasks.append(asyncio.create_task(self._metrics_loop()))
        self._tasks.append(asyncio.create_task(self._inactivity_monitor_loop()))

    async def stop(self) -> None:
        self._running = False
        for monitor in self._monitors.values():
            await monitor.stop()
        self._monitors.clear()
        for task in self._tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._tasks.clear()

    async def _quote_loop(self) -> None:
        while self._running:
            logger.info("[LOOP] Quote loop tick")
            active_pairs = self._select_active_pairs()
            if active_pairs:
                summary = [
                    f"{cfg.exchange_id.upper()}:{cfg.symbol}"
                    for cfg in active_pairs[:5]
                ]
                logger.info(
                    "[LOOP] Active quoting set (%s/%s): %s%s",
                    len(active_pairs),
                    len(self._pair_configs),
                    ", ".join(summary),
                    " ..." if len(active_pairs) > 5 else "",
                )
            await self._quote_manager.ensure_quotes(active_pairs)
            await asyncio.sleep(1.0)

    async def _balance_refresh_loop(self) -> None:
        while self._running:
            logger.info("[LOOP] Balance refresh tick")
            for exchange in self._adapter.available_exchanges():
                try:
                    await self._balance_cache.get_balances(exchange)
                except Exception as exc:
                    logger.debug("Balance refresh failed for %s: %s", exchange, exc)
            await asyncio.sleep(3.0)

    async def _inventory_guard_loop(self) -> None:
        while self._running:
            try:
                await self._run_inventory_guard()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.debug("Inventory guard error: %s", exc)
            await asyncio.sleep(self._inventory_check_interval)

    async def _hedge_refresh_loop(self) -> None:
        while self._running:
            try:
                await self._refresh_stale_hedges()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.debug("Hedge refresh error: %s", exc)
            await asyncio.sleep(self._hedge_refresh_interval)

    async def _metrics_loop(self) -> None:
        while self._running:
            try:
                metrics = self._fill_engine.get_metrics()
                hedges = await self._fill_engine.get_orders_by_tag("hedge")
                quotes = await self._fill_engine.get_orders_by_tag("quote")
                exposure_snapshot: Dict[str, Dict[str, str]] = {}
                for exchange in self._adapter.available_exchanges():
                    balances = await self._balance_cache.get_balances(exchange)
                    exposure_snapshot[exchange.upper()] = {
                        asset: str(amount)
                        for asset, amount in balances.items()
                        if amount > Decimal("0")
                    }
                logger.info(
                    "[METRICS] fills=%s pending=%s since_last_fill=%s hedges=%s quotes=%s fills_by_pair=%s exposure=%s",
                    metrics.get("total_fills_processed"),
                    metrics.get("pending_fills"),
                    metrics.get("seconds_since_last_fill"),
                    len(hedges),
                    len(quotes),
                    metrics.get("fills_by_pair"),
                    exposure_snapshot,
                )
                if self._last_rank_snapshot:
                    logger.info(
                        "[METRICS] ranking_top=%s",
                        self._last_rank_snapshot[:5],
                    )
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.debug("Metrics loop error: %s", exc)
            await asyncio.sleep(self._metrics_interval)

    async def _inactivity_monitor_loop(self) -> None:
        check_interval = 60.0
        warning_threshold = 600.0
        while self._running:
            await asyncio.sleep(check_interval)
            metrics = self._fill_engine.get_metrics()
            last_fill_age = metrics.get("seconds_since_last_fill")
            if last_fill_age is None:
                continue
            if last_fill_age < warning_threshold:
                continue
            now = time.time()
            if now - self._last_inactivity_warning < warning_threshold / 2:
                continue
            self._last_inactivity_warning = now
            logger.warning(
                "[OMS] ⚠️ No fills processed in %.1f minutes (total fills: %s, pending fills: %s)",
                last_fill_age / 60.0,
                metrics.get("total_fills_processed"),
                metrics.get("pending_fills"),
            )
            self._activate_cooldown(duration=180.0)
            for exchange in self._adapter.available_exchanges():
                try:
                    await self._balance_cache.get_balances(exchange)
                except Exception as exc:
                    logger.debug("[OMS] Balance refresh during inactivity failed: %s", exc)

    async def _run_inventory_guard(self) -> None:
        stable_quotes = {"USD", "USDC", "USDT", "GUSD"}
        priority = ("USD", "USDC", "USDT", "GUSD")
        for exchange_id in self._adapter.available_exchanges():
            try:
                balances = await self._balance_cache.get_balances(exchange_id)
                raw_balances = await self._adapter.fetch_balance(exchange_id)
            except Exception as exc:
                logger.debug(
                    "Inventory guard balance fetch failed for %s: %s",
                    exchange_id,
                    exc,
                )
                continue
            free_balances = raw_balances.get("free", {}) if isinstance(raw_balances, dict) else {}
            for currency, raw_amount in balances.items():
                total_amount = Decimal(str(raw_amount))
                free_amount = Decimal(str(free_balances.get(currency, 0)))
                usable_amount = min(total_amount, free_amount)
                logger.info(
                    "[INVENTORY] Inspecting %s on %s total=%s free=%s usable=%s",
                    currency,
                    exchange_id.upper(),
                    total_amount,
                    free_amount,
                    usable_amount,
                )
                if (
                    currency in stable_quotes
                    or usable_amount <= self._inventory_threshold
                ):
                    logger.info(
                        "[INVENTORY] Skipping %s on %s (stable or below threshold)",
                        currency,
                        exchange_id.upper(),
                    )
                    continue
                if self._fill_engine.has_active_sell_order(exchange_id, currency):
                    logger.info(
                        "[INVENTORY] Active hedge already exists for %s on %s",
                        currency,
                        exchange_id.upper(),
                    )
                    continue
                configs = self._pair_index.get(exchange_id, {}).get(currency, [])
                placed = False
                if configs:
                    ordered_configs = sorted(
                        configs,
                        key=lambda cfg: priority.index(cfg.symbol.split("/")[1])
                        if cfg.symbol.split("/")[1] in priority
                        else len(priority),
                    )
                    for cfg in ordered_configs:
                        logger.info(
                            "[INVENTORY] Attempting hedge via %s on %s amount=%s",
                            cfg.symbol,
                            exchange_id.upper(),
                            usable_amount,
                        )
                        placed = await self._place_inventory_hedge(cfg, usable_amount)
                        if placed:
                            break
                if not placed:
                    await self._liquidate_asset(
                        exchange_id, currency, usable_amount, priority
                    )

    async def _on_order_registered(self, order: ManagedOrder) -> None:
        if order.tag == "hedge":
            self._hedge_attempts[(order.exchange_id, order.symbol)] = 0
            logger.info(
                "[HEDGE] Tracking hedge %s %s order=%s",
                order.exchange_id.upper(),
                order.symbol,
                order.order_id,
            )

    async def _on_order_cancelled(self, order: ManagedOrder) -> None:
        if order.tag == "hedge":
            self._hedge_attempts.pop((order.exchange_id, order.symbol), None)
            logger.info(
                "[HEDGE] Cancelled tracked hedge %s %s order=%s",
                order.exchange_id.upper(),
                order.symbol,
                order.order_id,
            )

    async def _on_fill(self, order: ManagedOrder, fill: FillEvent) -> None:
        if order.tag == "hedge":
            self._hedge_attempts.pop((order.exchange_id, order.symbol), None)
        self._pair_cooldowns.pop((order.exchange_id, order.symbol), None)
        self._last_inactivity_warning = 0.0
        logger.info(
            "[FILL] %s %s filled amount=%s price=%s",
            order.exchange_id.upper(),
            order.symbol,
            fill.amount,
            fill.price,
        )
        pair_key = (order.exchange_id, order.symbol)
        stats = self._get_pair_stats(pair_key)
        stats["last_fill_ts"] = time.time()
        if order.side == OrderSide.BUY:
            self._position_tracker[pair_key].append((fill.amount, fill.price))
            logger.info(
                "[PNL] Recorded buy leg %s %s amount=%s price=%s",
                order.exchange_id.upper(),
                order.symbol,
                fill.amount,
                fill.price,
            )
        elif order.side == OrderSide.SELL:
            remaining = fill.amount
            profit = Decimal("0")
            fifo = self._position_tracker[pair_key]
            updated_fifo: List[Tuple[Decimal, Decimal]] = []
            entry_notional = Decimal("0")
            exit_notional = Decimal("0")
            for bought_amount, bought_price in fifo:
                if remaining <= Decimal("0"):
                    updated_fifo.append((bought_amount, bought_price))
                    continue
                matched = min(remaining, bought_amount)
                entry_value = matched * bought_price
                exit_value = matched * fill.price
                entry_notional += entry_value
                exit_notional += exit_value
                profit += exit_value - entry_value
                remaining -= matched
                leftover = bought_amount - matched
                if leftover > Decimal("0"):
                    updated_fifo.append((leftover, bought_price))
            if remaining > Decimal("0"):
                logger.warning(
                    "[PNL] SELL exceeded tracked inventory for %s %s remaining=%s",
                    order.exchange_id.upper(),
                    order.symbol,
                    remaining,
                )
            self._position_tracker[pair_key] = updated_fifo
            self._realized_pnl += profit
            self._realized_volume += fill.price * fill.amount
            self._trade_count += 1
            stats["trade_count"] += 1
            stats["pnl"] += profit
            stats["volume"] += exit_notional
            edge_bps = Decimal("0")
            if entry_notional > Decimal("0"):
                edge_bps = ((exit_notional / entry_notional) - Decimal("1")) * Decimal("10000")
                prev_avg = stats["avg_edge_bps"]
                trades = stats["trade_count"]
                if trades > 0:
                    stats["avg_edge_bps"] = (
                        (prev_avg * Decimal(trades - 1)) + edge_bps
                    ) / Decimal(trades)
                else:
                    stats["avg_edge_bps"] = edge_bps
            if profit > Decimal("0"):
                stats["wins"] += 1
                stats["loss_streak"] = 0
            if profit > Decimal("0"):
                self._wins += 1
            elif profit < Decimal("0"):
                stats["losses"] += 1
                stats["loss_streak"] += 1
                self._losses += 1
            else:
                stats["break_even"] += 1
                stats["loss_streak"] = 0
                self._break_even += 1
            if profit < Decimal("0") and stats["loss_streak"] >= 3:
                cooldown_period = 180.0
                until = time.time() + cooldown_period
                self._pair_cooldowns[(order.exchange_id, order.symbol)] = until
                logger.warning(
                    "[FILL] Activated cooldown for %s %s after %s consecutive losses (%.1fs)",
                    order.exchange_id.upper(),
                    order.symbol,
                    stats["loss_streak"],
                    cooldown_period,
                )
            self._log_pnl_summary(order.exchange_id)

    async def _place_inventory_hedge(self, cfg: PairConfig, amount: Decimal) -> bool:
        if amount <= self._inventory_threshold:
            return False
        if not self._adapter.is_symbol_supported(cfg.exchange_id, cfg.symbol):
            logger.info(
                "[INVENTORY] Market %s not supported on %s",
                cfg.symbol,
                cfg.exchange_id.upper(),
            )
            return False
        try:
            order_book = await self._adapter.fetch_order_book(
                cfg.exchange_id, cfg.symbol, depth=5
            )
        except Exception as exc:
            logger.debug(
                "[INVENTORY] Failed to fetch order book for %s on %s: %s",
                cfg.symbol,
                cfg.exchange_id,
                exc,
            )
            return False

        bids = order_book.get("bids") or []
        if not bids:
            logger.info(
                "[INVENTORY] No bids for %s on %s",
                cfg.symbol,
                cfg.exchange_id.upper(),
            )
            return False
        best_bid = Decimal(str(bids[0][0]))
        if best_bid <= 0:
            return False

        sell_amount = amount.quantize(Decimal("0.00001"), rounding=ROUND_DOWN)
        sell_value = sell_amount * best_bid
        min_notional = cfg.min_notional_usd if cfg else Decimal("5.00")
        if sell_value < self._dust_threshold:
            logger.info(
                "[INVENTORY] Dust position %s on %s value=%s < dust_threshold=%s",
                cfg.symbol,
                cfg.exchange_id.upper(),
                sell_value,
                self._dust_threshold,
            )
            return False
        if sell_value < min_notional:
            logger.info(
                "[INVENTORY] Sell amount below notional for %s on %s value=%s min=%s",
                cfg.symbol,
                cfg.exchange_id.upper(),
                sell_value,
                cfg.min_notional_usd,
            )
            return False

        order_type = "market" if cfg.exchange_id == "coinbase" else "limit"
        price: Optional[Decimal] = None
        if order_type == "limit":
            price = (best_bid * Decimal("0.999")).quantize(Decimal("0.00001"))

        logger.info(
            "[INVENTORY] Posting hedge sell %s on %s price=%s amount=%s",
            cfg.symbol,
            cfg.exchange_id.upper(),
            price if price is not None else "MARKET",
            sell_amount,
        )
        try:
            response = await self._adapter.create_order(
                cfg.exchange_id,
                cfg.symbol,
                OrderSide.SELL,
                amount=sell_amount,
                price=price,
                order_type=order_type,
            )
        except Exception as exc:
            logger.debug(
                "[INVENTORY] Failed to post hedge order for %s on %s: %s",
                cfg.symbol,
                cfg.exchange_id,
                exc,
            )
            return False

        order_id = response.get("id") or response.get("order_id")
        if not order_id:
            return False

        tracked_price = price if price is not None else best_bid
        managed = ManagedOrder(
            exchange_id=cfg.exchange_id,
            symbol=cfg.symbol,
            side=OrderSide.SELL,
            order_id=str(order_id),
            price=tracked_price,
            amount=sell_amount,
            tag="hedge",
        )
        await self._fill_engine.register_order(managed)
        logger.info(
            "[INVENTORY] Posted hedge sell %s on %s @ %s x%s",
            cfg.symbol,
            cfg.exchange_id.upper(),
            tracked_price,
            sell_amount,
        )
        return True

    def _rebuild_pair_maps(self) -> None:
        index: Dict[str, Dict[str, List[PairConfig]]] = {}
        for cfg in self._pair_configs:
            base, _ = cfg.symbol.split("/")
            per_exchange = index.setdefault(cfg.exchange_id, {})
            per_exchange.setdefault(base, []).append(cfg)
        self._pair_index = index

    async def _startup_cleanup(self) -> None:
        exchanges = self._adapter.available_exchanges()
        for exchange_id in exchanges:
            logger.info("[STARTUP] Cancelling open orders on %s", exchange_id.upper())
            await self._cancel_open_orders(exchange_id)
            logger.info("[STARTUP] Flattening inventory on %s", exchange_id.upper())
            await self._flatten_inventory(exchange_id)
            await self._balance_cache.get_balances(exchange_id)
        self._pair_configs = await self._filter_supported_pairs(self._pair_configs)
        self._fill_engine = InstantFillResponseEngine(
            self._adapter,
            self._db,
            self._pair_configs,
            order_registered_cb=self._on_order_registered,
            order_cancelled_cb=self._on_order_cancelled,
            fill_callback=self._on_fill,
        )
        self._quote_manager = DualSideQuoteManager(
            self._adapter,
            self._fill_engine,
            self._balance_cache,
            self._pair_configs,
            self._pair_cooldowns,
            self._fee_floor_bps,
        )
        self._hedge_attempts.clear()
        self._rebuild_pair_maps()
        self._last_inactivity_warning = 0.0

    def _activate_cooldown(self, duration: float) -> None:
        until = time.time() + duration
        for cfg in self._pair_configs:
            self._pair_cooldowns[(cfg.exchange_id, cfg.symbol)] = until
        logger.warning(
            "[QUOTE] Activated cooldown for all pairs duration=%.1fs",
            duration,
        )

    def _log_pnl_summary(self, exchange_id: str) -> None:
        win_rate = (
            (self._wins / self._trade_count) * 100
            if self._trade_count > 0
            else 0.0
        )
        avg_profit = (
            self._realized_pnl / Decimal(str(self._trade_count))
            if self._trade_count > 0
            else Decimal("0")
        )
        logger.info(
            "[PNL] ✅✅ Total PnL: $%.4f | Trades: %s | Win rate: %.2f%% | Wins: %s | Losses: %s | Break-even: %s | Avg profit: $%.4f | Exchange: %s",
            float(self._realized_pnl),
            self._trade_count,
            win_rate,
            self._wins,
            self._losses,
            self._break_even,
            float(avg_profit),
            exchange_id.upper(),
        )

    async def _cancel_open_orders(self, exchange_id: str) -> None:
        try:
            open_orders = await self._adapter.fetch_open_orders(exchange_id)
        except Exception as exc:
            logger.debug("[CLEANUP] Unable to fetch open orders on %s: %s", exchange_id, exc)
            return

        for order in open_orders:
            order_id = str(order.get("id")) if order.get("id") is not None else None
            symbol = order.get("symbol") or order.get("info", {}).get("symbol")
            if not order_id or not symbol:
                continue
            try:
                await self._adapter.cancel_order(exchange_id, symbol, order_id)
                logger.info("[CLEANUP] Cancelled %s order %s", exchange_id.upper(), order_id)
            except Exception as exc:
                logger.debug("[CLEANUP] Failed to cancel %s order %s: %s", exchange_id, order_id, exc)

    async def _flatten_inventory(self, exchange_id: str) -> None:
        try:
            balances = await self._balance_cache.get_balances(exchange_id)
            raw_balances = await self._adapter.fetch_balance(exchange_id)
        except Exception as exc:
            logger.debug("[CLEANUP] Unable to fetch balances for %s: %s", exchange_id, exc)
            return

        stable = {"USD", "USDC", "USDT", "GUSD"}
        quotes_priority = ["USD", "USDC", "USDT", "GUSD"]
        free_balances = raw_balances.get("free", {}) if isinstance(raw_balances, dict) else {}

        for currency, raw_amount in balances.items():
            total_amount = Decimal(str(raw_amount))
            free_amount = Decimal(str(free_balances.get(currency, 0)))
            usable_amount = min(total_amount, free_amount)
            if currency in stable or usable_amount <= Decimal("0.00001"):
                continue
            await self._liquidate_asset(exchange_id, currency, usable_amount, quotes_priority)

    async def _liquidate_asset(
        self,
        exchange_id: str,
        base_currency: str,
        amount: Decimal,
        quotes_priority: Sequence[str],
    ) -> bool:
        for quote in quotes_priority:
            symbol = f"{base_currency}/{quote}"
            cfg = next(
                (cfg for cfg in self._pair_configs if cfg.exchange_id == exchange_id and cfg.symbol == symbol),
                None,
            )
            if not self._adapter.is_symbol_supported(exchange_id, symbol):
                logger.info(
                    "[CLEANUP] %s not supported on %s during flatten",
                    symbol,
                    exchange_id.upper(),
                )
                continue
            try:
                order_book = await self._adapter.fetch_order_book(exchange_id, symbol, depth=5)
            except Exception:
                continue
            bids = order_book.get("bids") or []
            if not bids:
                continue
            best_bid = Decimal(str(bids[0][0]))
            if best_bid <= 0:
                continue

            sell_amount = amount.quantize(Decimal("0.00001"), rounding=ROUND_DOWN)
            sell_value = sell_amount * best_bid
            min_notional = cfg.min_notional_usd if cfg else Decimal("5.00")
            if sell_value < self._dust_threshold:
                logger.info(
                    "[CLEANUP] %s on %s treated as dust value=%s < dust_threshold=%s",
                    symbol,
                    exchange_id.upper(),
                    sell_value,
                    self._dust_threshold,
                )
                continue
            if sell_value < min_notional:
                logger.info(
                    "[CLEANUP] Order value below minimum for %s on %s value=%s min=%s",
                    symbol,
                    exchange_id.upper(),
                    sell_value,
                    min_notional,
                )
                continue

            order_type = "market" if exchange_id == "coinbase" else "limit"
            price = None
            if order_type == "limit":
                price = (best_bid * Decimal("0.999")).quantize(Decimal("0.00001"))

            logger.info(
                "[CLEANUP] Attempting flatten %s on %s amount=%s price=%s",
                symbol,
                exchange_id.upper(),
                sell_amount,
                price if price is not None else "MARKET",
            )
            try:
                response = await self._adapter.create_order(
                    exchange_id,
                    symbol,
                    OrderSide.SELL,
                    amount=sell_amount,
                    price=price,
                    order_type=order_type,
                )
            except Exception as exc:
                logger.debug(
                    "[CLEANUP] Failed to flatten %s on %s: %s",
                    symbol,
                    exchange_id,
                    exc,
                )
                continue
            order_id = response.get("id") or response.get("order_id")
            if order_id:
                tracked_price = price if price is not None else best_bid
                managed = ManagedOrder(
                    exchange_id=exchange_id,
                    symbol=symbol,
                    side=OrderSide.SELL,
                    order_id=str(order_id),
                    price=tracked_price,
                    amount=sell_amount,
                    tag="hedge",
                )
                await self._fill_engine.register_order(managed)
            logger.info(
                "[CLEANUP] Flattened %s %.8f @ %s on %s",
                symbol,
                sell_amount,
                price if price is not None else "MARKET",
                exchange_id.upper(),
            )
            return True
        logger.debug(
            "[CLEANUP] Unable to flatten %s %.8f on %s (no viable market)",
            base_currency,
            amount,
            exchange_id,
        )
        return False

    async def _refresh_stale_hedges(self) -> None:
        hedges = await self._fill_engine.get_orders_by_tag("hedge")
        if not hedges:
            return
        now = time.time()
        for hedge in hedges:
            age = now - hedge.created_at
            if age < self._hedge_max_age:
                continue
            logger.info(
                "[OMS] 🔁 Refreshing stale hedge %s %s order=%s age=%.1fs",
                hedge.exchange_id.upper(),
                hedge.symbol,
                hedge.order_id,
                age,
            )
            try:
                await self._adapter.cancel_order(
                    hedge.exchange_id, hedge.symbol, hedge.order_id
                )
                await self._fill_engine.mark_cancelled(
                    hedge.exchange_id, hedge.symbol, hedge.side
                )
            except Exception as exc:
                logger.warning(
                    "[OMS] Unable to cancel stale hedge %s %s: %s",
                    hedge.exchange_id.upper(),
                    hedge.symbol,
                    exc,
                )
                continue

            try:
                order_book = await self._adapter.fetch_order_book(
                    hedge.exchange_id, hedge.symbol, depth=5
                )
            except Exception as exc:
                logger.warning(
                    "[OMS] Cannot refresh hedge %s %s due to book error: %s",
                    hedge.exchange_id.upper(),
                    hedge.symbol,
                    exc,
                )
                continue

            bids = order_book.get("bids") or []
            asks = order_book.get("asks") or []
            attempts = self._hedge_attempts.get((hedge.exchange_id, hedge.symbol), 0)
            order_type = "limit"
            order_params: Optional[Dict[str, Any]] = None

            if hedge.side == OrderSide.SELL and bids:
                candidate = Decimal(str(bids[0][0]))
                price = max(candidate, hedge.price).quantize(Decimal("0.00001"))
            elif hedge.side == OrderSide.BUY and asks:
                candidate = Decimal(str(asks[0][0]))
                price = min(candidate, hedge.price).quantize(Decimal("0.00001"))
            else:
                price = None

            if price is None:
                logger.warning(
                    "[OMS] Cannot determine refreshed price for hedge %s %s",
                    hedge.exchange_id.upper(),
                    hedge.symbol,
                )
                continue

            if price == hedge.price:
                logger.debug(
                    "[HEDGE] Retaining entry price %s for %s %s (attempts=%s)",
                    price,
                    hedge.exchange_id.upper(),
                    hedge.symbol,
                    attempts,
                )
            else:
                logger.info(
                    "[HEDGE] Refreshing hedge %s %s attempts=%s new_price=%s entry_price=%s",
                    hedge.exchange_id.upper(),
                    hedge.symbol,
                    attempts,
                    price,
                    hedge.price,
                )

            try:
                response = await self._adapter.create_order(
                    hedge.exchange_id,
                    hedge.symbol,
                    hedge.side,
                    amount=hedge.amount,
                    price=price,
                    order_type=order_type,
                    params=order_params,
                )
            except Exception as exc:
                logger.error(
                    "[OMS] Failed to recreate hedge %s %s: %s",
                    hedge.exchange_id.upper(),
                    hedge.symbol,
                    exc,
                )
                continue

            order_id = response.get("id") or response.get("order_id")
            if not order_id:
                logger.error(
                    "[OMS] Hedge refresh missing order id for %s %s",
                    hedge.exchange_id.upper(),
                    hedge.symbol,
                )
                continue

            refreshed = ManagedOrder(
                exchange_id=hedge.exchange_id,
                symbol=hedge.symbol,
                side=hedge.side,
                order_id=str(order_id),
                price=price,
                amount=hedge.amount,
                tag="hedge",
            )
            await self._fill_engine.register_order(refreshed)
            self._hedge_attempts[(hedge.exchange_id, hedge.symbol)] = attempts + 1
            logger.info(
                "[OMS] 🔄 Hedge refreshed %s %s new_order=%s price=%s",
                hedge.exchange_id.upper(),
                hedge.symbol,
                order_id,
                price,
            )

    async def _filter_supported_pairs(
        self, pair_configs: Sequence[PairConfig]
    ) -> List[PairConfig]:
        filtered: List[PairConfig] = []
        markets_cache: Dict[str, Dict[str, Any]] = {}
        for cfg in pair_configs:
            exchange_id = cfg.exchange_id
            if exchange_id not in markets_cache:
                try:
                    exchange = self._adapter._manager.get_exchange(exchange_id)
                    markets_cache[exchange_id] = exchange.markets
                except Exception:
                    markets_cache[exchange_id] = {}
            markets = markets_cache.get(exchange_id, {})
            if cfg.symbol in markets:
                filtered.append(cfg)
            else:
                logger.debug(
                    "[FILTER] Skipping %s on %s (symbol not supported)",
                    cfg.symbol,
                    exchange_id,
                )
        return filtered


