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

        for exchange_name, exchange_cfg in self.config.exchanges.items():
            client = ExchangeClient(exchange_cfg)
            self.exchange_clients[exchange_name] = client
            capital = self.config.capital_per_exchange.get(exchange_name, Decimal("0"))
            for pair_cfg in exchange_cfg.markets:
                base, quote = self._split_symbol(pair_cfg.symbol)
                market_data = MarketDataFeed(client, pair_cfg.symbol)
                inventory = InventoryManager(client, base_currency=base, quote_currency=quote, risk=self.config.risk)
                quoter = Quoter(pair_cfg, capital)
                order_manager = OrderManager(client, self.config.paths, self.config.strategy)
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

        volatility = runtime.market_data.volatility.volatility()
        pause_reason = runtime.inventory.should_pause(snapshot.mid_price, volatility)
        if pause_reason:
            logger.warning("Pausing %s: %s", runtime.cfg.symbol, pause_reason)
            await runtime.order_manager.cancel_all(runtime.cfg.symbol)
            return

        now = time.time()
        if now - runtime.last_quote_time >= runtime.cfg.order_refresh_seconds:
            await self._refresh_quotes(runtime, snapshot.mid_price, snapshot.spread_pct, volatility)
            runtime.last_quote_time = now

        if now - runtime.last_reconcile_time >= 5:
            await runtime.order_manager.reconcile(runtime.cfg.symbol)
            runtime.last_reconcile_time = now

    async def _refresh_quotes(
        self,
        runtime: PairRuntime,
        mid_price: Decimal,
        spread_pct: Decimal,
        volatility: Decimal,
    ) -> None:
        inventory_skew = Decimal("0")
        if self.config.strategy.enable_inventory_skew:
            inventory_skew = runtime.inventory.compute_skew(mid_price)

        decision = runtime.quoter.compute(mid_price, spread_pct, volatility, inventory_skew)
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

        await runtime.order_manager.cancel_all(runtime.cfg.symbol)

        try:
            bid_order = await runtime.order_manager.place_limit_order(
                runtime.cfg.symbol,
                "buy",
                decision.bid_amount,
                decision.bid_price,
            )
            ask_order = await runtime.order_manager.place_limit_order(
                runtime.cfg.symbol,
                "sell",
                decision.ask_amount,
                decision.ask_price,
            )
            runtime.active_orders = {
                "buy": bid_order,
                "sell": ask_order,
            }
        except ExchangeError as exc:
            logger.error("Failed placing quotes for %s: %s", runtime.cfg.symbol, exc)

    @staticmethod
    def _split_symbol(symbol: str) -> tuple[str, str]:
        resolved = symbol.replace("-", "/")
        base, quote = resolved.split("/")
        return base, quote

