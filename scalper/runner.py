from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from decimal import Decimal
from typing import Dict

from .config import PairConfig, ScalperConfig
from .exchange import ExchangeCredentials, RestExchangeClient
from .execution import ExecutionManager
from .market_data import MarketDataPoller
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
                snapshot = poller.latest()
                if not snapshot:
                    await asyncio.sleep(self._config.settings.poll_interval_s)
                    continue
                stable_balance = await self._fetch_stable_balance(client, pair.quote)
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
                    await execution.sync(intent)
                await asyncio.sleep(self._config.settings.poll_interval_s)
        finally:
            await poller.stop()

    async def _fetch_stable_balance(self, client: RestExchangeClient, currency: str) -> Decimal:
        try:
            balance = await client.fetch_balance()
            total = balance.get("total") or {}
            amount = Decimal(str(total.get(currency, 0)))
            return amount
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Failed to fetch balance for %s: %s", currency, exc)
            return Decimal("0")
