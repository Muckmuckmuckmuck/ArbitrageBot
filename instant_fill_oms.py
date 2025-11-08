from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any, Deque, Dict, Iterable, List, Optional, Sequence, Tuple

from coinbase_gemini_exchanges import CoinbaseGeminiExchangeManager
from database_manager import DatabaseManager, TradeRecord

logger = logging.getLogger(__name__)


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
    order_size_usd: Decimal = Decimal("3.00")
    min_spread_bps: int = 30  # 0.30%
    max_quote_interval_s: float = 5.0
    min_depth_usd: Decimal = Decimal("10000")
    min_notional_usd: Decimal = Decimal("5.00")
    price_improve_bps: int = 5  # 0.05%


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

    async def create_order(
        self,
        exchange_id: str,
        symbol: str,
        side: OrderSide,
        *,
        amount: Decimal,
        price: Optional[Decimal] = None,
        order_type: str = "limit",
    ) -> Dict:
        return await self._manager.create_order(
            exchange_id=exchange_id,
            symbol=symbol,
            order_type=order_type,
            side=side.value,
            amount=float(amount),
            price=float(price) if price is not None else None,
        )

    async def cancel_order(
        self, exchange_id: str, symbol: str, order_id: str
    ) -> None:
        await self._manager.cancel_order(exchange_id, order_id, symbol)

    async def fetch_order_book(
        self, exchange_id: str, symbol: str, depth: int = 10
    ) -> Dict:
        return await self._manager.fetch_order_book(exchange_id, symbol, depth)

    async def fetch_open_orders(
        self, exchange_id: str, symbol: Optional[str] = None
    ) -> List[Dict]:
        return await self._manager.fetch_open_orders(exchange_id, symbol)

    async def fetch_trades(
        self,
        exchange_id: str,
        symbol: Optional[str] = None,
        since: Optional[int] = None,
    ) -> List[Dict]:
        return await self._manager.fetch_my_trades(exchange_id, symbol, since)

    async def fetch_balance(self, exchange_id: str) -> Dict:
        return await self._manager.fetch_balance(exchange_id)

    async def fetch_ticker(self, exchange_id: str, symbol: str) -> Dict:
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

    async def _maybe_refresh(self, exchange_id: str) -> None:
        now = time.time()
        if now - self._last_refresh.get(exchange_id, 0) < self._refresh_interval:
            return
        raw = await self._adapter.fetch_balance(exchange_id)
        balances: Dict[str, Decimal] = {}
        free = raw.get("free", {})
        total = raw.get("total", {})
        for currency, value in total.items():
            free_value = Decimal(str(free.get(currency, 0)))
            total_value = Decimal(str(value))
            balances[currency] = max(free_value, total_value)
        self._balances[exchange_id] = balances
        self._last_refresh[exchange_id] = now


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
    ) -> None:
        self._adapter = adapter
        self._db = db_manager
        self._latency_warning_ms = latency_warning_ms

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
            "failed_opposite_orders": self._metrics["opposite_failures"],
            "average_latency_ms": avg_latency,
            "p95_latency_ms": p95_latency,
            "pending_fills": len(self._pending_trades),
        }

    def get_active_order(
        self, exchange_id: str, symbol: str, side: OrderSide
    ) -> Optional[ManagedOrder]:
        return self._orders_by_pair.get((exchange_id, symbol, side))

    def reserved_quote(self, exchange_id: str, quote: str) -> Decimal:
        total = Decimal("0")
        for order in self._orders.values():
            if order.exchange_id != exchange_id or order.side != OrderSide.BUY:
                continue
            base, order_quote = order.symbol.split("/")
            if order_quote == quote:
                total += order.price * order.amount
        return total

    def reserved_base(self, exchange_id: str, base: str) -> Decimal:
        total = Decimal("0")
        for order in self._orders.values():
            if order.exchange_id != exchange_id or order.side != OrderSide.SELL:
                continue
            order_base, _ = order.symbol.split("/")
            if order_base == base:
                total += order.amount
        return total

    async def register_order(self, order: ManagedOrder) -> None:
        key = (order.exchange_id, order.order_id)
        side_key = (order.exchange_id, order.symbol, order.side)
        async with self._lock:
            self._orders[key] = order
            self._orders_by_pair[side_key] = order

    async def mark_cancelled(
        self, exchange_id: str, symbol: str, side: OrderSide
    ) -> None:
        side_key = (exchange_id, symbol, side)
        async with self._lock:
            existing = self._orders_by_pair.pop(side_key, None)
            if existing:
                self._orders.pop((exchange_id, existing.order_id), None)

    async def enqueue_fill(self, fill: FillEvent) -> None:
        async with self._lock:
            self._pending_trades.append(fill)

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

        base, quote = filled_order.symbol.split("/")
        side = OrderSide.SELL if filled_order.side == OrderSide.BUY else OrderSide.BUY

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
        amount = fill.amount.quantize(Decimal("0.00001"))

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
    ) -> None:
        self._adapter = adapter
        self._response_engine = response_engine
        self._balance_cache = balance_cache
        self._pair_configs = list(pair_configs)
        self._last_quote_time: Dict[Tuple[str, str], float] = {}

    async def ensure_quotes(self) -> None:
        for cfg in self._pair_configs:
            now = time.time()
            last = self._last_quote_time.get((cfg.exchange_id, cfg.symbol), 0.0)
            if now - last < cfg.max_quote_interval_s:
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

    async def _ensure_pair(self, cfg: PairConfig) -> None:
        try:
            order_book = await self._adapter.fetch_order_book(
                cfg.exchange_id, cfg.symbol, depth=5
            )
        except Exception:
            return
        if not order_book["bids"] or not order_book["asks"]:
            return

        best_bid = Decimal(str(order_book["bids"][0][0]))
        best_ask = Decimal(str(order_book["asks"][0][0]))
        bid_depth = sum(Decimal(str(entry[1])) * Decimal(str(entry[0])) for entry in order_book["bids"][:3])
        ask_depth = sum(Decimal(str(entry[1])) * Decimal(str(entry[0])) for entry in order_book["asks"][:3])

        if bid_depth < cfg.min_depth_usd or ask_depth < cfg.min_depth_usd:
            logger.debug(
                "[QUOTE] Depth too low for %s (%s/%s)",
                cfg.symbol,
                bid_depth,
                ask_depth,
            )
            return

        mid = (best_bid + best_ask) / Decimal("2")
        min_spread = Decimal(cfg.min_spread_bps) / Decimal("10000")
        spread = max((best_ask - best_bid) / mid, min_spread)
        buy_price = mid * (Decimal("1") - spread / Decimal("2"))
        sell_price = mid * (Decimal("1") + spread / Decimal("2"))
        buy_price = buy_price.quantize(Decimal("0.00001"))
        sell_price = sell_price.quantize(Decimal("0.00001"))

        order_value = max(cfg.order_size_usd, Decimal(cfg.min_notional_usd))
        buy_amount = (order_value / buy_price).quantize(Decimal("0.00001"))
        sell_amount = (order_value / sell_price).quantize(Decimal("0.00001"))

        base, quote = cfg.symbol.split("/")
        quote_balance = await self._balance_cache.get_balance(cfg.exchange_id, quote)
        base_balance = await self._balance_cache.get_balance(cfg.exchange_id, base)

        quote_reserved = self._response_engine.reserved_quote(cfg.exchange_id, quote)
        base_reserved = self._response_engine.reserved_base(cfg.exchange_id, base)

        usable_quote = max(Decimal("0"), quote_balance - quote_reserved)
        usable_base = max(Decimal("0"), base_balance - base_reserved)

        max_buy_amount = (
            usable_quote / (buy_price * Decimal("1.01"))
        ).quantize(Decimal("0.00001")) if buy_price > 0 else Decimal("0")
        buy_amount = min(buy_amount, max_buy_amount)

        sell_amount = min(sell_amount, usable_base.quantize(Decimal("0.00001")))

        need_buy = buy_amount > Decimal("0") and (buy_amount * buy_price) >= cfg.min_notional_usd
        need_sell = sell_amount > Decimal("0") and (sell_amount * sell_price) >= cfg.min_notional_usd

        await self._sync_side(cfg, OrderSide.BUY, buy_amount, buy_price, need_buy)
        await self._sync_side(cfg, OrderSide.SELL, sell_amount, sell_price, need_sell)

    async def _sync_side(
        self,
        cfg: PairConfig,
        side: OrderSide,
        amount: Decimal,
        price: Decimal,
        allowed: bool,
    ) -> None:
        existing = self._response_engine.get_active_order(
            cfg.exchange_id, cfg.symbol, side
        )
        if not allowed:
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
            return

        if existing:
            await self._adapter.cancel_order(
                cfg.exchange_id, cfg.symbol, existing.order_id
            )
            await self._response_engine.mark_cancelled(
                cfg.exchange_id, cfg.symbol, side
            )
            # refresh balances after cancellation to avoid stale locked funds
            await self._balance_cache.get_balances(cfg.exchange_id)

        response = await self._adapter.create_order(
            cfg.exchange_id,
            cfg.symbol,
            side,
            amount=amount,
            price=price,
            order_type="limit",
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
    ) -> None:
        self._adapter = adapter
        self._response_engine = response_engine
        self._exchange_id = exchange_id
        self._poll_interval = poll_interval
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
            await asyncio.sleep(self._poll_interval)

    async def _poll_once(self) -> None:
        for symbol in self._symbols:
            trades = await self._adapter.fetch_trades(
                self._exchange_id,
                symbol,
                since=self._last_trade_ts,
            )
            if trades:
                self._last_trade_ts = max(t.get("timestamp", 0) for t in trades)

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
                open_orders.extend(
                    await self._adapter.fetch_open_orders(self._exchange_id, symbol)
                )
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
        self._balance_cache = BalanceCache(adapter)
        self._fill_engine = InstantFillResponseEngine(
            adapter, db_manager, self._pair_configs
        )
        self._quote_manager = DualSideQuoteManager(
            adapter, self._fill_engine, self._balance_cache, self._pair_configs
        )
        self._monitors: Dict[str, WebSocketFillMonitor] = {}
        self._tasks: List[asyncio.Task] = []
        self._running = False

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        await self._startup_cleanup()
        symbols_by_exchange: Dict[str, List[str]] = defaultdict(list)
        for cfg in self._pair_configs:
            symbols_by_exchange[cfg.exchange_id].append(cfg.symbol)

        for exchange_id, symbols in symbols_by_exchange.items():
            monitor = WebSocketFillMonitor(
                self._adapter, self._fill_engine, exchange_id
            )
            await monitor.start(symbols)
            self._monitors[exchange_id] = monitor

        self._tasks.append(asyncio.create_task(self._fill_engine.retry_pending_fills()))
        self._tasks.append(asyncio.create_task(self._quote_loop()))
        self._tasks.append(asyncio.create_task(self._balance_refresh_loop()))

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
            await self._quote_manager.ensure_quotes()
            await asyncio.sleep(1.0)

    async def _balance_refresh_loop(self) -> None:
        while self._running:
            for exchange in self._adapter.available_exchanges():
                try:
                    await self._balance_cache.get_balances(exchange)
                except Exception as exc:
                    logger.debug("Balance refresh failed for %s: %s", exchange, exc)
            await asyncio.sleep(3.0)

    async def _startup_cleanup(self) -> None:
        exchanges = self._adapter.available_exchanges()
        for exchange_id in exchanges:
            await self._cancel_open_orders(exchange_id)
            await self._flatten_inventory(exchange_id)
            await self._balance_cache.get_balances(exchange_id)
        self._pair_configs = await self._filter_supported_pairs(self._pair_configs)
        self._fill_engine = InstantFillResponseEngine(
            self._adapter,
            self._db,
            self._pair_configs,
        )
        self._quote_manager = DualSideQuoteManager(
            self._adapter,
            self._fill_engine,
            self._balance_cache,
            self._pair_configs,
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
        except Exception as exc:
            logger.debug("[CLEANUP] Unable to fetch balances for %s: %s", exchange_id, exc)
            return

        stable = {"USD", "USDC", "USDT", "GUSD"}
        quotes_priority = ["USD", "USDC", "USDT", "GUSD"]

        for currency, raw_amount in balances.items():
            amount = Decimal(str(raw_amount))
            if currency in stable or amount <= Decimal("0.00001"):
                continue
            await self._liquidate_asset(exchange_id, currency, amount, quotes_priority)

    async def _liquidate_asset(
        self,
        exchange_id: str,
        base_currency: str,
        amount: Decimal,
        quotes_priority: Sequence[str],
    ) -> None:
        for quote in quotes_priority:
            symbol = f"{base_currency}/{quote}"
            cfg = next(
                (cfg for cfg in self._pair_configs if cfg.exchange_id == exchange_id and cfg.symbol == symbol),
                None,
            )
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

            sell_amount = amount.quantize(Decimal("0.00001"))
            sell_value = sell_amount * best_bid
            min_notional = cfg.min_notional_usd if cfg else Decimal("5.00")
            if sell_value < min_notional:
                continue

            order_type = "market" if exchange_id == "coinbase" else "limit"
            price = None
            if order_type == "limit":
                price = (best_bid * Decimal("0.999")).quantize(Decimal("0.00001"))

            try:
                await self._adapter.create_order(
                    exchange_id,
                    symbol,
                    OrderSide.SELL,
                    amount=sell_amount,
                    price=price,
                    order_type=order_type,
                )
                logger.info(
                    "[CLEANUP] Flattened %s %.8f @ %s on %s",
                    symbol,
                    sell_amount,
                    price if price is not None else "MARKET",
                    exchange_id.upper(),
                )
                return
            except Exception as exc:
                logger.debug(
                    "[CLEANUP] Failed to flatten %s on %s: %s",
                    symbol,
                    exchange_id,
                    exc,
                )
        logger.debug(
            "[CLEANUP] Unable to flatten %s %.8f on %s (no viable market)",
            base_currency,
            amount,
            exchange_id,
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


