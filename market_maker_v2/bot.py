from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN
from typing import Dict, Optional

from .config import BotConfig, PairConfig
from .exchange import ExchangeClient, ExchangeError
from .inventory import InventoryManager
from .market_data import MarketDataFeed, MarketSnapshot
from .order_manager import OrderManager, OrderRecord
from .quoter import Quoter

logger = logging.getLogger(__name__)


@dataclass
class PairRuntime:
    exchange: str
    cfg: PairConfig
    market_data: MarketDataFeed
    inventory: InventoryManager
    quoter: Quoter
    order_manager: OrderManager
    active_orders: Dict[str, Dict[int, OrderRecord]]
    order_last_checked: Dict[str, Dict[int, float]]
    last_snapshot: Optional[MarketSnapshot] = None  # type: ignore[name-defined]
    dust_amount: Decimal = Decimal("0")
    last_quote_time: float = 0.0
    last_reconcile_time: float = 0.0
    last_status_log: float = 0.0


class MarketMakerBot:
    """High-level orchestrator for the new modular market-making system."""

    def __init__(self, config: BotConfig) -> None:
        self.config = config
        self.exchange_clients: Dict[str, ExchangeClient] = {}
        self.pairs: Dict[str, Dict[str, PairRuntime]] = defaultdict(dict)
        self._running = False
        self._tasks: Dict[str, asyncio.Task[None]] = {}
        self.initial_nav = config.starting_capital_usd
        self.high_water_nav = self.initial_nav
        self.global_pause_until = 0.0

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        logger.info("Starting market maker v2...")

        simulate = self.config.strategy.simulate_mode

        for exchange_name, exchange_cfg in self.config.exchanges.items():
            client = ExchangeClient(exchange_cfg)
            self.exchange_clients[exchange_name] = client
            capital = self.config.capital_per_exchange.get(exchange_name, Decimal("0"))
            for pair_cfg in exchange_cfg.markets:
                if not await self._passes_initial_screen(client, pair_cfg):
                    logger.info("Skipping %s/%s - liquidity screen failed", exchange_name, pair_cfg.symbol)
                    continue
                base, quote = self._split_symbol(pair_cfg.symbol)
                market_data = MarketDataFeed(client, pair_cfg.symbol)
                inventory = InventoryManager(
                    client,
                    base_currency=base,
                    quote_currency=quote,
                    risk=self.config.risk,
                    simulate_mode=simulate,
                    initial_base=Decimal("0"),
                    initial_quote=capital,
                )
                quoter = Quoter(pair_cfg, capital)
                order_manager = OrderManager(
                    client,
                    self.config.paths,
                    self.config.strategy,
                    maker_fee_bps=exchange_cfg.maker_fee_bps,
                    taker_fee_bps=exchange_cfg.taker_fee_bps,
                    simulate_mode=simulate,
                )
                runtime = PairRuntime(
                    exchange=exchange_name,
                    cfg=pair_cfg,
                    market_data=market_data,
                    inventory=inventory,
                    quoter=quoter,
                    order_manager=order_manager,
                    active_orders={"buy": {}, "sell": {}},
                    order_last_checked={"buy": {}, "sell": {}},
                )
                self.pairs[exchange_name][pair_cfg.symbol] = runtime
                await market_data.start()
                await inventory.start()

            await self._startup_cleanup(exchange_name)
            self._tasks[exchange_name] = asyncio.create_task(self._run_exchange_loop(exchange_name))

    async def stop(self) -> None:
        self._running = False
        for task in self._tasks.values():
            task.cancel()
        for exchange, pair_map in self.pairs.items():
            for runtime in pair_map.values():
                await runtime.market_data.stop()
                await runtime.inventory.stop()
                await runtime.order_manager.cancel_all(runtime.cfg.symbol)
            await self.exchange_clients[exchange].close()

    async def _run_exchange_loop(self, exchange_name: str) -> None:
        client = self.exchange_clients[exchange_name]
        while self._running:
            pair_map = self.pairs[exchange_name]
            for symbol, runtime in pair_map.items():
                try:
                    await self._process_pair(runtime)
                except Exception as exc:  # noqa: BLE001
                    logger.exception("Error processing %s %s: %s", exchange_name, symbol, exc)
            await asyncio.sleep(1.0)

    async def _process_pair(self, runtime: PairRuntime) -> None:
        healthy, reason = runtime.market_data.health()
        if not healthy:
            logger.debug("Market data unhealthy for %s: %s", runtime.cfg.symbol, reason)
            return
        snapshot = runtime.market_data.snapshot
        if snapshot is None:
            return
        runtime.last_snapshot = snapshot

        current_time = time.time()
        if current_time < self.global_pause_until:
            logger.warning("Global pause active; skipping %s", runtime.cfg.symbol)
            await runtime.order_manager.cancel_all(runtime.cfg.symbol)
            self._clear_active_orders(runtime)
            return

        if self._check_global_drawdown():
            self.global_pause_until = current_time + self.config.risk.circuit_breaker_cooldown_seconds
            logger.error("Global drawdown exceeded limit; pausing all trading for %ds", self.config.risk.circuit_breaker_cooldown_seconds)
            await runtime.order_manager.cancel_all(runtime.cfg.symbol)
            self._clear_active_orders(runtime)
            return

        if self._pair_exposure_exceeded(runtime, snapshot):
            logger.warning("Exposure limit hit for %s; flattening", runtime.cfg.symbol)
            await runtime.order_manager.cancel_all(runtime.cfg.symbol)
            self._clear_active_orders(runtime)
            await self._flatten_inventory(runtime, snapshot)
            return

        spread_pct = snapshot.spread_pct
        volatility = runtime.market_data.volatility.volatility()
        if self.config.strategy.simulate_mode:
            self._simulate_fills(runtime, snapshot)
        pause_reason = runtime.inventory.should_pause(snapshot.mid_price, volatility)
        if pause_reason:
            logger.warning("Pausing %s: %s", runtime.cfg.symbol, pause_reason)
            await runtime.order_manager.cancel_all(runtime.cfg.symbol)
            self._clear_active_orders(runtime)
            return

        now = time.time()
        if now - runtime.last_quote_time >= runtime.cfg.order_refresh_seconds:
            await self._refresh_quotes(runtime, snapshot, spread_pct, volatility)
            runtime.last_quote_time = now

        if now - runtime.last_reconcile_time >= 5:
            await runtime.order_manager.reconcile(runtime.cfg.symbol)
            await self._handle_order_updates(runtime, snapshot, spread_pct, volatility)
            runtime.last_reconcile_time = now
        else:
            await self._handle_order_updates(runtime, snapshot, spread_pct, volatility)

        self._log_pair_status(runtime, snapshot)

    async def _refresh_quotes(
        self,
        runtime: PairRuntime,
        snapshot,
        spread_pct: Decimal,
        volatility: Decimal,
    ) -> None:
        inventory_skew = Decimal("0")
        if self.config.strategy.enable_inventory_skew:
            inventory_skew = runtime.inventory.compute_skew(snapshot.mid_price)

        decision = runtime.quoter.compute(
            snapshot.mid_price,
            spread_pct,
            volatility,
            inventory_skew,
            snapshot.bid_depth_usd,
            snapshot.ask_depth_usd,
        )
        if decision.bids and decision.asks:
            logger.info(
                "Quoting %s | layers=%d | top bid=%s x%s top ask=%s x%s | spread=%.2fbps | skew=%.2f%%",
                runtime.cfg.symbol,
                max(len(decision.bids), len(decision.asks)),
                decision.bids[0][0],
                decision.bids[0][1],
                decision.asks[0][0],
                decision.asks[0][1],
                decision.spread_bps,
                decision.inventory_skew * Decimal("100"),
            )
        await self._ensure_quote_layers(runtime, snapshot, "buy", decision.bids)
        await self._ensure_quote_layers(runtime, snapshot, "sell", decision.asks)

    @staticmethod
    def _split_symbol(symbol: str) -> tuple[str, str]:
        resolved = symbol.replace("-", "/")
        base, quote = resolved.split("/")
        return base, quote

    def _simulate_fills(self, runtime: PairRuntime, snapshot) -> None:
        if not self.config.strategy.simulate_mode:
            return
        for side, orders in runtime.active_orders.items():
            for level, order in list(orders.items()):
                if order.status != "open":
                    continue
                if side == "buy" and snapshot.best_ask <= order.price:
                    updated = runtime.order_manager.mark_filled(order, snapshot.best_ask)
                    orders[level] = updated
                elif side == "sell" and snapshot.best_bid >= order.price:
                    updated = runtime.order_manager.mark_filled(order, snapshot.best_bid)
                    orders[level] = updated

    async def _handle_order_updates(
        self,
        runtime: PairRuntime,
        snapshot,
        spread_pct: Decimal,
        volatility: Decimal,
    ) -> None:
        for side in ("buy", "sell"):
            active_side = runtime.active_orders[side]
            last_checked_side = runtime.order_last_checked[side]
            for level, order in list(active_side.items()):
                latest = runtime.order_manager.get(order.client_order_id)
                if latest is None:
                    active_side.pop(level, None)
                    last_checked_side.pop(level, None)
                    continue
                previous_filled = order.filled
                now = time.time()
                last_checked = last_checked_side.get(level, 0)
                if now - last_checked >= 1.5:
                    refreshed = await runtime.order_manager.refresh_order(runtime.cfg.symbol, latest)
                    last_checked_side[level] = now
                    if refreshed:
                        latest = refreshed
                active_side[level] = latest
                if latest.status == "open" and latest.filled > previous_filled:
                    runtime.quoter.record_fill(side, True)
                if latest.status in {"filled", "closed"}:
                    runtime.quoter.record_fill(side, True)
                    active_side.pop(level, None)
                    last_checked_side.pop(level, None)
                    fee = runtime.order_manager.fee_for(side, latest.amount, latest.price, maker=True)
                    runtime.inventory.apply_fill(side, latest.amount, latest.price, fee)
                    logger.info(
                        "Filled %s L%d %s @ %s amount=%s",
                        runtime.cfg.symbol,
                        level,
                        side,
                        latest.price,
                        latest.amount,
                    )
                    if self.config.strategy.hedge_on_fill and side == "buy":
                        await self._hedge_after_fill(runtime, snapshot, latest)
                    runtime.last_quote_time = 0
                elif latest.status == "cancelled":
                    runtime.quoter.record_fill(side, False)
                    active_side.pop(level, None)
                    last_checked_side.pop(level, None)

        inventory_skew = Decimal("0")
        if self.config.strategy.enable_inventory_skew:
            inventory_skew = runtime.inventory.compute_skew(snapshot.mid_price)
        decision = runtime.quoter.compute(
            snapshot.mid_price,
            spread_pct,
            volatility,
            inventory_skew,
            snapshot.bid_depth_usd,
            snapshot.ask_depth_usd,
        )
        await self._ensure_quote_layers(runtime, snapshot, "buy", decision.bids)
        await self._ensure_quote_layers(runtime, snapshot, "sell", decision.asks)

    async def _ensure_quote_layers(
        self,
        runtime: PairRuntime,
        snapshot,
        side: str,
        targets: list[tuple[Decimal, Decimal]],
    ) -> None:
        active_side = runtime.active_orders[side]
        # Cancel excess layers
        for level in list(active_side.keys()):
            if level < 0:
                continue
            if level >= len(targets):
                await runtime.order_manager.cancel_order(runtime.cfg.symbol, active_side[level])
                runtime.order_last_checked[side].pop(level, None)
                active_side.pop(level, None)

        for idx, (price, amount) in enumerate(targets):
            await self._ensure_quote_level(runtime, snapshot, side, idx, price, amount)

    async def _ensure_quote_level(
        self,
        runtime: PairRuntime,
        snapshot,
        side: str,
        level: int,
        target_price: Decimal,
        target_amount: Decimal,
    ) -> Optional[OrderRecord]:
        if target_amount <= Decimal("0"):
            return None

        active_side = runtime.active_orders[side]
        existing = active_side.get(level)
        now = time.time()
        needs_replace = False
        if existing and existing.status == "open":
            price_denominator = existing.price if existing.price > 0 else target_price
            price_delta = abs(existing.price - target_price) / price_denominator
            age = now - existing.created_at
            if price_delta >= runtime.cfg.price_requote_pct or age >= runtime.cfg.order_expiry_seconds:
                needs_replace = True
            if not needs_replace:
                return existing
            await runtime.order_manager.cancel_order(runtime.cfg.symbol, existing)
            active_side.pop(level, None)
            runtime.order_last_checked[side].pop(level, None)

        inventory_snapshot = runtime.inventory.snapshot
        if inventory_snapshot is None:
            logger.debug("Skipping ensure level %d for %s on %s - no inventory snapshot", level, side, runtime.cfg.symbol)
            return None

        amount = target_amount
        total_amount = amount
        if side == "sell":
            reserved = sum(
                order.amount
                for lvl, order in active_side.items()
                if lvl != level and lvl >= 0 and order.status == "open"
            )
            available_base = max(Decimal("0"), inventory_snapshot.base_balance - reserved)
            if available_base <= Decimal("0"):
                return None
            total_amount += runtime.dust_amount
            total_amount = min(total_amount, available_base)
            if total_amount <= Decimal("0"):
                return None
        else:
            reserved = sum(
                order.price * order.amount * Decimal("1.01")
                for lvl, order in active_side.items()
                if lvl != level and lvl >= 0 and order.status == "open"
            )
            available_quote = max(Decimal("0"), inventory_snapshot.quote_balance - reserved)
            if available_quote <= Decimal("0"):
                return None
            max_affordable = available_quote / (target_price * Decimal("1.01"))
            total_amount = min(total_amount, max_affordable)
            if total_amount <= Decimal("0"):
                return None

        order_value = target_price * total_amount
        if order_value < runtime.cfg.min_order_usd:
            if side == "sell":
                runtime.dust_amount = total_amount
                logger.info(
                    "Accumulating dust for %s: amount=%s (~$%.2f) awaiting threshold",
                    runtime.cfg.symbol,
                    total_amount,
                    order_value,
                )
            return None

        amount = total_amount.quantize(Decimal("0.00001"))
        if side == "sell":
            runtime.dust_amount = Decimal("0")

        try:
            new_order = await runtime.order_manager.place_limit_order(runtime.cfg.symbol, side, amount, target_price)
        except ExchangeError as exc:
            logger.error("Failed to place %s level %d for %s: %s", side, level, runtime.cfg.symbol, exc)
            return None

        active_side[level] = new_order
        runtime.order_last_checked[side][level] = now
        logger.info(
            "Posted %s L%d for %s @ %s x%s",
            side.upper(),
            level,
            runtime.cfg.symbol,
            target_price,
            amount,
        )
        return new_order

    def _count_active_orders(self, runtime: PairRuntime) -> tuple[int, int]:
        buy_count = 0
        sell_count = 0
        for level, order in runtime.active_orders["buy"].items():
            if level >= 0 and order.status == "open":
                buy_count += 1
        for level, order in runtime.active_orders["sell"].items():
            if level >= 0 and order.status == "open":
                sell_count += 1
        return buy_count, sell_count

    async def _passes_initial_screen(self, client: ExchangeClient, pair_cfg: PairConfig) -> bool:
        if not pair_cfg.allow_dynamic_watchlist:
            return True
        try:
            ticker = await client.fetch_ticker(pair_cfg.symbol)
        except ExchangeError as exc:
            logger.warning("Failed liquidity ticker fetch for %s: %s", pair_cfg.symbol, exc)
            return False
        volume_raw = ticker.get("quoteVolume") or ticker.get("quote_volume") or ticker.get("baseVolume") or 0
        volume = Decimal(str(volume_raw)) if volume_raw else Decimal("0")
        if volume < pair_cfg.min_volume_usd:
            logger.info(
                "Volume screen failed for %s: %.0f < %.0f",
                pair_cfg.symbol,
                volume,
                pair_cfg.min_volume_usd,
            )
            return False
        try:
            order_book = await client.fetch_order_book(pair_cfg.symbol, 5)
        except ExchangeError:
            return True
        bid_depth = sum(Decimal(str(p)) * Decimal(str(q)) for p, q in (order_book.get("bids") or []))
        ask_depth = sum(Decimal(str(p)) * Decimal(str(q)) for p, q in (order_book.get("asks") or []))
        if bid_depth < pair_cfg.min_depth_usd or ask_depth < pair_cfg.min_depth_usd:
            logger.info(
                "Depth screen failed for %s: bid %.0f ask %.0f min %.0f",
                pair_cfg.symbol,
                bid_depth,
                ask_depth,
                pair_cfg.min_depth_usd,
            )
            return False
        return True

    def _compute_total_nav(self) -> Decimal:
        total = Decimal("0")
        for runtime_map in self.pairs.values():
            for runtime in runtime_map.values():
                snap = runtime.last_snapshot
                inv = runtime.inventory.snapshot
                if snap and inv:
                    total += inv.base_balance * snap.mid_price + inv.quote_balance
        return total

    def _check_global_drawdown(self) -> bool:
        nav = self._compute_total_nav()
        if nav <= Decimal("0"):
            return False
        self.high_water_nav = max(self.high_water_nav, nav)
        drawdown = (self.high_water_nav - nav) / self.high_water_nav if self.high_water_nav > 0 else Decimal("0")
        return drawdown >= self.config.risk.max_drawdown_pct

    def _pair_exposure_exceeded(self, runtime: PairRuntime, snapshot: MarketSnapshot) -> bool:
        inv = runtime.inventory.snapshot
        if inv is None:
            return False
        base_value = inv.base_balance * snapshot.mid_price
        capital = self.config.capital_per_exchange.get(runtime.exchange, self.config.starting_capital_usd)
        if capital <= 0:
            return False
        return base_value > capital * self.config.risk.max_pair_exposure_pct

    def _log_pair_status(self, runtime: PairRuntime, snapshot) -> None:
        now = time.time()
        if now - runtime.last_status_log < 10:
            return
        buy_count, sell_count = self._count_active_orders(runtime)
        inventory_snapshot = runtime.inventory.snapshot
        base_bal = float(inventory_snapshot.base_balance) if inventory_snapshot else 0.0
        quote_bal = float(inventory_snapshot.quote_balance) if inventory_snapshot else 0.0
        logger.info(
            "[STATUS] %s | BUY=%d SELL=%d | base=%.6f quote=$%.2f | mid=%s",
            runtime.cfg.symbol,
            buy_count,
            sell_count,
            base_bal,
            quote_bal,
            snapshot.mid_price,
        )
        runtime.last_status_log = now

    async def _hedge_after_fill(self, runtime: PairRuntime, snapshot, filled_order: OrderRecord) -> None:
        inventory_snapshot = runtime.inventory.snapshot
        if inventory_snapshot is None or filled_order.amount <= Decimal("0"):
            return
        available = min(inventory_snapshot.base_balance, filled_order.amount)
        if available <= Decimal("0"):
            return
        hedge_price = snapshot.best_ask * Decimal("0.999")
        hedge_price = hedge_price.quantize(Decimal("0.01"))
        try:
            hedge_order = await runtime.order_manager.place_limit_order(
                runtime.cfg.symbol,
                "sell",
                available.quantize(Decimal("0.00001")),
                hedge_price,
            )
            level = -int(time.time() * 1000)
            runtime.active_orders["sell"][level] = hedge_order
            runtime.order_last_checked["sell"][level] = time.time()
            logger.info(
                "Hedge sell posted for %s @ %s x%s",
                runtime.cfg.symbol,
                hedge_price,
                available,
            )
        except ExchangeError as exc:
            logger.warning("Hedge placement failed for %s: %s", runtime.cfg.symbol, exc)

    def _clear_active_orders(self, runtime: PairRuntime) -> None:
        runtime.active_orders["buy"].clear()
        runtime.active_orders["sell"].clear()
        runtime.order_last_checked["buy"].clear()
        runtime.order_last_checked["sell"].clear()

    async def _startup_cleanup(self, exchange_name: str) -> None:
        pair_map = self.pairs.get(exchange_name)
        if not pair_map:
            return

        logger.info("Startup cleanup for %s: cancelling open orders and flattening balances", exchange_name)
        seen_managers: set[int] = set()
        for runtime in pair_map.values():
            manager_id = id(runtime.order_manager)
            if manager_id in seen_managers:
                continue
            try:
                await runtime.order_manager.cancel_all_force()
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to cancel open orders on %s for %s: %s", exchange_name, runtime.cfg.symbol, exc)
            seen_managers.add(manager_id)

        for runtime in pair_map.values():
            await self._force_flatten_inventory(runtime)

    async def _force_flatten_inventory(self, runtime: PairRuntime) -> None:
        snapshot = await runtime.inventory.fetch_balances()
        if snapshot is not None:
            runtime.inventory.snapshot = snapshot
        if snapshot is None:
            return

        total_amount = snapshot.base_balance + runtime.dust_amount
        if total_amount <= Decimal("0"):
            return

        try:
            ticker = await runtime.order_manager.client.fetch_ticker(runtime.cfg.symbol)
        except ExchangeError as exc:
            logger.warning("Startup flatten skipped for %s: ticker fetch failed (%s)", runtime.cfg.symbol, exc)
            return

        bid_raw = ticker.get("bid") or ticker.get("last") or ticker.get("close")
        if not bid_raw:
            logger.warning("Startup flatten skipped for %s: no bid available", runtime.cfg.symbol)
            return

        bid_price = Decimal(str(bid_raw))
        if bid_price <= 0:
            logger.warning("Startup flatten skipped for %s: invalid bid %s", runtime.cfg.symbol, bid_price)
            return

        amount = total_amount.quantize(Decimal("0.00001"), rounding=ROUND_DOWN)
        if amount <= Decimal("0"):
            return

        order_value = amount * bid_price
        if order_value < runtime.cfg.min_order_usd:
            logger.info(
                "Startup flatten skipped for %s: value $%.2f below minimum $%.2f",
                runtime.cfg.symbol,
                float(order_value),
                float(runtime.cfg.min_order_usd),
            )
            runtime.dust_amount = total_amount
            return

        try:
            logger.info(
                "Startup flatten for %s: selling %.8f @ ~%s (%s)",
                runtime.cfg.symbol,
                float(amount),
                bid_price,
                runtime.exchange,
            )
            await runtime.order_manager.client.create_market_order(
                runtime.cfg.symbol,
                "sell",
                amount,
                params={"post_only": False},
            )
        except ExchangeError as exc:
            error_text = str(exc).lower()
            if "market" in error_text or "post only" in error_text:
                fallback_price = bid_price * Decimal("0.999")
                try:
                    await runtime.order_manager.client.create_limit_order(
                        runtime.cfg.symbol,
                        "sell",
                        amount,
                        fallback_price,
                        params={"post_only": False},
                    )
                    logger.info(
                        "Startup flatten fallback for %s: limit sell %.8f @ %s submitted",
                        runtime.cfg.symbol,
                        float(amount),
                        fallback_price,
                    )
                except ExchangeError as limit_exc:
                    logger.warning("Startup flatten failed for %s (limit fallback): %s", runtime.cfg.symbol, limit_exc)
                    return
            else:
                logger.warning("Startup flatten failed for %s: %s", runtime.cfg.symbol, exc)
                return

        await asyncio.sleep(1.0)
        refreshed = await runtime.inventory.fetch_balances()
        if refreshed:
            runtime.inventory.snapshot = refreshed
            runtime.dust_amount = Decimal("0")

    async def _flatten_inventory(self, runtime: PairRuntime, snapshot: MarketSnapshot) -> None:
        inv = runtime.inventory.snapshot
        if inv is None:
            return
        total_amount = inv.base_balance + runtime.dust_amount
        if total_amount <= Decimal("0"):
            return
        amount = total_amount.quantize(Decimal("0.00001"))
        price = max(snapshot.best_bid * Decimal("0.999"), snapshot.mid_price * Decimal("0.995"))
        price = price.quantize(Decimal("0.01"))
        order_value = amount * price
        if order_value < runtime.cfg.min_order_usd:
            runtime.dust_amount = total_amount
            return
        try:
            await runtime.order_manager.place_limit_order(runtime.cfg.symbol, "sell", amount, price)
            runtime.dust_amount = Decimal("0")
            logger.info("Flatten order placed for %s @ %s x%s", runtime.cfg.symbol, price, amount)
        except ExchangeError as exc:
            logger.warning("Flatten placement failed for %s: %s", runtime.cfg.symbol, exc)

