from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from collections import defaultdict
from decimal import Decimal
from typing import Dict, Sequence, Set, Optional

from .config import PairConfig, ScalperConfig
from .exchange import ExchangeCredentials, RestExchangeClient
from .execution import ExecutionManager
from .hedging import compute_hedge_price
from .market_data import MarketDataPoller
from .pnl import PnLTracker
from .risk import RiskManager
from .state import PairRuntimeState
from .strategy import QuotePlanner, QuoteIntent
from .telemetry import PlanTelemetry, Telemetry

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
        self._telemetry = Telemetry()
        self._tasks: Dict[str, asyncio.Task[None]] = {}
        self._rotation_task: Optional[asyncio.Task[None]] = None
        self._running = False
        self._enabled_pairs = self._filter_pairs(config.pairs)
        self._active_pairs: Set[str] = {pair.symbol for pair in self._enabled_pairs}

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
        if not self._enabled_pairs:
            logger.error("[STARTUP] No trading pairs enabled—check API credentials")
        for pair in self._enabled_pairs:
            task = asyncio.create_task(self._run_pair(pair))
            self._tasks[pair.symbol] = task
        self._rotation_task = asyncio.create_task(self._rotation_loop())

    async def stop(self) -> None:
        self._running = False
        await asyncio.gather(*self._tasks.values(), return_exceptions=True)
        self._tasks.clear()
        if self._rotation_task:
            self._rotation_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._rotation_task
            self._rotation_task = None
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
                if pair.symbol not in self._active_pairs:
                    await execution.cancel_all_quotes()
                    await execution.prune_stale_hedges(self._config.settings.hedge_stale_seconds)
                    await asyncio.sleep(self._config.settings.poll_interval_s)
                    continue
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

                intent = self._planner.plan(
                    pair,
                    state,
                    snapshot,
                    stable_balance,
                    self._config.settings.fast_fill_latency_ms,
                    self._config.settings.fast_fill_clip_bps,
                    self._config.settings.slow_fill_clip_bps,
                )
                if intent:
                    self._telemetry.plan(
                        PlanTelemetry(
                            exchange=pair.exchange,
                            symbol=pair.symbol,
                            buy_size=intent.buy_size,
                            buy_price=intent.buy_price,
                            sell_size=intent.sell_size,
                            sell_price=intent.sell_price,
                            net_edge_bps=state.recent_net_edges[-1] if state.recent_net_edges else Decimal("0"),
                            reason=intent.reason,
                        )
                    )
                    await execution.sync_quotes(intent)
                else:
                    await execution.cancel_all_quotes()
                    self._telemetry.skip(pair.exchange, pair.symbol, "planner_rejected")

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

    async def _rotation_loop(self) -> None:
        while self._running:
            await asyncio.sleep(max(5.0, self._config.settings.poll_interval_s * 5))
            scores = []
            for pair in self._enabled_pairs:
                state = self._states[pair.symbol]
                recent_edges = list(state.recent_net_edges)
                edge_avg = sum(recent_edges) / Decimal(len(recent_edges)) if recent_edges else Decimal("-100")
                stats = self._pnl.get_stats(f"{pair.exchange}:{pair.symbol}")
                penalty = Decimal(stats.losses * 5 + state.skip_reasons.get("edge_target", 0) * 2 + state.skip_reasons.get("notional", 0))
                score = float(edge_avg - penalty)
                scores.append((score, pair.symbol))
            scores.sort(reverse=True, key=lambda item: item[0])
            allowed = {symbol for _, symbol in scores[: self._config.settings.max_active_pairs]}
            if allowed != self._active_pairs:
                logger.info("[ROTATION] Active pairs -> %s", ", ".join(sorted(allowed)))
            self._active_pairs = allowed

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
                state.update_probe(
                    success=result == "win",
                    cfg_base=pair.base_probe_size_usd,
                    cfg_step=pair.probe_step_usd,
                    cfg_max=pair.max_probe_size_usd,
                )
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
            elif side == "sell" and amount > 0:
                hedge_price = compute_hedge_price(price, side, self._config.settings.hedge_fee_guard_bps)
                await execution.place_hedge("buy", amount, hedge_price)

    def _filter_pairs(self, pairs: Sequence[PairConfig]) -> Sequence[PairConfig]:
        enabled = []
        for pair in pairs:
            creds = self._config.venue_keys.get(pair.exchange, {})
            api_key = (creds or {}).get("api_key", "").strip()
            api_secret = (creds or {}).get("api_secret", "").strip()
            if not api_key or not api_secret:
                logger.warning(
                    "[STARTUP] Skipping %s %s due to missing credentials",
                    pair.exchange.upper(),
                    pair.symbol,
                )
                continue
            enabled.append(pair)
        return enabled
