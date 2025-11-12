from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict
from decimal import Decimal
from typing import Dict

from .config import PairConfig, ScalperConfig
from .exchange import ExchangeCredentials, RestExchangeClient
from .execution import ExecutionManager
from .hedging import compute_hedge_price
from .market_data import MarketDataPoller
from .pnl import PnLTracker
from .risk import RiskManager
from .state import PairRuntimeState
from .strategy import QuotePlanner

logger = logging.getLogger(__name__)


class ScalperEngine:
    """Coordinates market data polling and strategy execution via REST only."""

    def __init__(self, config: ScalperConfig) -> None:
        self._config = config
        self._clients: Dict[str, RestExchangeClient] = {}
        self._states: Dict[str, PairRuntimeState] = defaultdict(PairRuntimeState)
        self._planner = QuotePlanner()
        self._pnl = PnLTracker()
        self._risk = RiskManager(config.settings, self._pnl)
        self._tasks: Dict[str, asyncio.Task[None]] = {}
        self._running = False

    async def _client_for(self, exchange: str) -> RestExchangeClient:
        if exchange not in self._clients:
            creds_data = self._config.venue_keys.get(exchange)
            if not creds_data:
                raise RuntimeError(f"Missing credentials for {exchange}")
            creds = ExchangeCredentials(
                api_key=creds_data["api_key"],
                api_secret=creds_data["api_secret"],
                passphrase=creds_data.get("passphrase"),
            )
            self._clients[exchange] = RestExchangeClient(exchange, creds)
        return self._clients[exchange]

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        for pair in self._config.pairs:
            task = asyncio.create_task(self._run_pair(pair))
            self._tasks[pair.symbol] = task

    async def stop(self) -> None:
        self._running = False
        await asyncio.gather(*self._tasks.values(), return_exceptions=True)
        self._tasks.clear()
        await asyncio.gather(*(client.close() for client in self._clients.values()), return_exceptions=True)

    async def _run_pair(self, pair: PairConfig) -> None:
        client = await self._client_for(pair.exchange)
        poller = MarketDataPoller(client, pair.symbol, interval_s=self._config.settings.poll_interval_s)
        execution = ExecutionManager(client, pair.symbol)
        state = self._states[pair.symbol]
        await poller.start()
        try:
            while self._running:
                await self._consume_trades(client, pair, state, execution)
                snapshot = poller.latest()
                if not snapshot:
                    await asyncio.sleep(self._config.settings.poll_interval_s)
                    continue
                stable_balance = await self._fetch_stable_balance(client, pair.quote)
                assessment = self._risk.evaluate(pair, state, stable_balance)
                if not assessment.allowed:
                    logger.info(
                        "[RISK] Skip %s %s reason=%s",
                        pair.exchange.upper(),
                        pair.symbol,
                        assessment.reason,
                    )
                    await execution.cancel_all_quotes()
                    await execution.prune_stale_hedges(self._config.settings.hedge_stale_seconds)
                    await asyncio.sleep(self._config.settings.poll_interval_s)
                    continue

                intent = self._planner.plan(pair, state, snapshot, stable_balance)
                if intent:
                    logger.info(
                        "[PLAN] %s %s buy=%s@%s sell=%s@%s %s",
                        pair.exchange.upper(),
                        pair.symbol,
                        intent.buy_size,
                        intent.buy_price,
                        intent.sell_size,
                        intent.sell_price,
                        intent.reason,
                    )
                    await execution.sync_quotes(intent)
                else:
                    await execution.cancel_all_quotes()

                await execution.prune_stale_hedges(self._config.settings.hedge_stale_seconds)
                await asyncio.sleep(self._config.settings.poll_interval_s)
        finally:
            await poller.stop()
            await execution.cancel_all()

    async def _fetch_stable_balance(self, client: RestExchangeClient, currency: str) -> Decimal:
        try:
            balance = await client.fetch_balance()
            total = balance.get("total") or {}
            amount = Decimal(str(total.get(currency, 0)))
            return amount
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Failed to fetch balance for %s: %s", currency, exc)
            return Decimal("0")

    async def _consume_trades(self, client: RestExchangeClient, pair: PairConfig, state: PairRuntimeState, execution: ExecutionManager) -> None:
        since = state.last_trade_fetch_ts or None
        try:
            trades = await client.fetch_my_trades(pair.symbol, since=since, limit=100)
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug("fetch_my_trades failed for %s %s: %s", pair.exchange, pair.symbol, exc)
            return

        if not trades:
            return

        for trade in trades:
            trade_id = str(trade.get("id") or trade.get("orderId") or "")
            if state.seen_trade(trade_id):
                continue
            timestamp = int(trade.get("timestamp") or int(time.time() * 1000))
            state.last_trade_fetch_ts = max(state.last_trade_fetch_ts, timestamp + 1)
            side = str(trade.get("side") or "").lower()
            amount = Decimal(str(trade.get("amount") or trade.get("filled") or 0))
            price = Decimal(str(trade.get("price") or 0))
            fee_info = trade.get("fee") or {}
            fee_cost = Decimal(str(fee_info.get("cost", 0))) if fee_info else Decimal("0")
            order_ref = str(trade.get("order") or trade.get("order_id") or trade.get("clientOrderId") or "")
            execution.mark_filled(order_ref or trade_id)
            pair_key = f"{pair.exchange}:{pair.symbol}"
            realized, result = self._pnl.process_fill(pair_key, state, side, amount, price, fee_cost)
            if result in {"win", "loss", "flat"}:
                self._risk.register_fill_result(state, result)
            if realized != 0:
                logger.info(
                    "[FILL] %s %s side=%s amount=%s price=%s realized=%s",
                    pair.exchange.upper(),
                    pair.symbol,
                    side,
                    amount,
                    price,
                    realized.quantize(Decimal("0.0001")),
                )
            if side == "buy" and amount > 0:
                hedge_price = compute_hedge_price(price, side, self._config.settings.hedge_fee_guard_bps)
                await execution.place_hedge("sell", amount, hedge_price)
