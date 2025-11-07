from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, Optional

from .config import BotConfig, PairConfig
from .exchange import ExchangeClient, ExchangeError
from .inventory import InventoryManager
from .market_data import MarketDataFeed
from .order_manager import OrderManager, OrderRecord
from .quoter import Quoter

logger = logging.getLogger(__name__)


@dataclass
class PairRuntime:
    cfg: PairConfig
    market_data: MarketDataFeed
    inventory: InventoryManager
    quoter: Quoter
    order_manager: OrderManager
    active_orders: Dict[str, OrderRecord]
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
                    cfg=pair_cfg,
                    market_data=market_data,
                    inventory=inventory,
                    quoter=quoter,
                    order_manager=order_manager,
                    active_orders={},
                )
                self.pairs[exchange_name][pair_cfg.symbol] = runtime
                await market_data.start()
                await inventory.start()

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

        spread_pct = snapshot.spread_pct
        volatility = runtime.market_data.volatility.volatility()
        if self.config.strategy.simulate_mode:
            self._simulate_fills(runtime, snapshot)
        pause_reason = runtime.inventory.should_pause(snapshot.mid_price, volatility)
        if pause_reason:
            logger.warning("Pausing %s: %s", runtime.cfg.symbol, pause_reason)
            await runtime.order_manager.cancel_all(runtime.cfg.symbol)
            runtime.active_orders.clear()
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

        decision = runtime.quoter.compute(snapshot.mid_price, spread_pct, volatility, inventory_skew)
        logger.info(
            "Quoting %s | bid=%s x%s ask=%s x%s spread=%.2fbps skew=%.2f%%",
            runtime.cfg.symbol,
            decision.bid_price,
            decision.bid_amount,
            decision.ask_price,
            decision.ask_amount,
            decision.spread_bps,
            decision.inventory_skew * Decimal("100"),
        )

        await self._ensure_quote_side(runtime, snapshot, "buy", decision.bid_price, decision.bid_amount)
        await self._ensure_quote_side(runtime, snapshot, "sell", decision.ask_price, decision.ask_amount)

    @staticmethod
    def _split_symbol(symbol: str) -> tuple[str, str]:
        resolved = symbol.replace("-", "/")
        base, quote = resolved.split("/")
        return base, quote

    def _simulate_fills(self, runtime: PairRuntime, snapshot) -> None:
        if not self.config.strategy.simulate_mode:
            return
        for side, order in list(runtime.active_orders.items()):
            if order.status != "open":
                continue
            if side == "buy" and snapshot.best_ask <= order.price:
                updated = runtime.order_manager.mark_filled(order, snapshot.best_ask)
                runtime.active_orders[side] = updated
            elif side == "sell" and snapshot.best_bid >= order.price:
                updated = runtime.order_manager.mark_filled(order, snapshot.best_bid)
                runtime.active_orders[side] = updated

    async def _handle_order_updates(
        self,
        runtime: PairRuntime,
        snapshot,
        spread_pct: Decimal,
        volatility: Decimal,
    ) -> None:
        inventory_skew = Decimal("0")
        if self.config.strategy.enable_inventory_skew:
            inventory_skew = runtime.inventory.compute_skew(snapshot.mid_price)
        decision: Optional[Quoter] = None  # placeholder for type hints
        for side, order in list(runtime.active_orders.items()):
            latest = runtime.order_manager.get(order.client_order_id)
            if latest is None:
                runtime.active_orders.pop(side, None)
                continue
            runtime.active_orders[side] = latest
            if latest.status in {"filled", "cancelled"}:
                runtime.active_orders.pop(side, None)
                if latest.status == "filled":
                    fee = runtime.order_manager.fee_for(side, latest.amount, latest.price, maker=True)
                    runtime.inventory.apply_fill(side, latest.amount, latest.price, fee)
                    logger.info(
                        "Filled %s %s @ %s amount=%s",
                        runtime.cfg.symbol,
                        side,
                        latest.price,
                        latest.amount,
                    )
                    runtime.last_quote_time = 0
        missing_sides = [
            side
            for side in ("buy", "sell")
            if side not in runtime.active_orders or runtime.active_orders[side].status != "open"
        ]
        if missing_sides:
            quote_decision = runtime.quoter.compute(snapshot.mid_price, spread_pct, volatility, inventory_skew)
            if "buy" in missing_sides:
                await self._ensure_quote_side(runtime, snapshot, "buy", quote_decision.bid_price, quote_decision.bid_amount, force=True)
            if "sell" in missing_sides:
                await self._ensure_quote_side(runtime, snapshot, "sell", quote_decision.ask_price, quote_decision.ask_amount, force=True)

    async def _ensure_quote_side(
        self,
        runtime: PairRuntime,
        snapshot,
        side: str,
        target_price: Decimal,
        target_amount: Decimal,
        force: bool = False,
    ) -> Optional[OrderRecord]:
        if target_amount <= Decimal("0"):
            return None

        existing = runtime.active_orders.get(side)
        now = time.time()
        needs_replace = force
        if existing and existing.status == "open":
            price_denominator = existing.price if existing.price > 0 else target_price
            price_delta = abs(existing.price - target_price) / price_denominator
            age = now - existing.created_at
            if price_delta >= runtime.cfg.price_requote_pct or age >= runtime.cfg.order_expiry_seconds:
                needs_replace = True
            if not needs_replace:
                return existing
            await runtime.order_manager.cancel_order(runtime.cfg.symbol, existing)
            runtime.active_orders.pop(side, None)

        inventory_snapshot = runtime.inventory.snapshot
        if inventory_snapshot is None:
            logger.debug("Skipping ensure for %s on %s - no inventory snapshot yet", side, runtime.cfg.symbol)
            return None

        amount = target_amount
        if side == "sell":
            available_base = inventory_snapshot.base_balance
            if available_base <= Decimal("0"):
                logger.debug("%s sell ensure skipped - zero base balance", runtime.cfg.symbol)
                return None
            if amount > available_base:
                amount = available_base.quantize(Decimal("0.00001"))
        else:
            available_quote = inventory_snapshot.quote_balance
            if available_quote <= Decimal("0"):
                logger.debug("%s buy ensure skipped - zero quote balance", runtime.cfg.symbol)
                return None
            required_quote = target_price * amount * Decimal("1.01")
            if required_quote > available_quote:
                amount = (available_quote / (target_price * Decimal("1.01"))).quantize(Decimal("0.00001"))

        if amount <= Decimal("0"):
            logger.debug("%s ensure skipped - adjusted amount <= 0", runtime.cfg.symbol)
            return None

        order_value = target_price * amount
        if order_value < runtime.cfg.min_order_usd:
            logger.debug(
                "%s ensure skipped - order value %.2f below minimum %.2f",
                runtime.cfg.symbol,
                order_value,
                runtime.cfg.min_order_usd,
            )
            return None

        try:
            new_order = await runtime.order_manager.place_limit_order(runtime.cfg.symbol, side, amount, target_price)
            runtime.active_orders[side] = new_order
            logger.info(
                "Posted %s order for %s @ %s x%s",
                side.upper(),
                runtime.cfg.symbol,
                target_price,
                amount,
            )
            return new_order
        except ExchangeError as exc:
            logger.error("Failed to place %s order for %s: %s", side, runtime.cfg.symbol, exc)
            return None

    def _count_active_orders(self, runtime: PairRuntime) -> tuple[int, int]:
        buy_count = 0
        sell_count = 0
        for order in runtime.order_manager.store.fetch_open(runtime.cfg.symbol):
            if order.side == "buy":
                buy_count += 1
            elif order.side == "sell":
                sell_count += 1
        return buy_count, sell_count

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

