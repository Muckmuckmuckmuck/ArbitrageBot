from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from collections import defaultdict
from decimal import Decimal, ROUND_DOWN
from typing import Dict, Sequence, Set, Optional, List, Tuple

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
from .discovery import OpportunityScanner, PairSnapshot, PairCatalog

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
        self._catalog = PairCatalog(config, config.pairs)
        self._scanner = OpportunityScanner(config, self._client_for)
        self._pair_configs: Dict[str, PairConfig] = {
            self._pair_key(pair.exchange, pair.symbol): pair for pair in config.pairs
        }
        self._tasks: Dict[str, asyncio.Task[None]] = {}
        self._rotation_task: Optional[asyncio.Task[None]] = None
        self._running = False
        self._enabled_pairs = self._filter_pairs(config.pairs)
        initial_keys = [self._pair_key(pair.exchange, pair.symbol) for pair in self._enabled_pairs]
        self._active_pairs: Set[str] = set(initial_keys[: self._config.settings.max_active_pairs])

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
            await self._clients[exchange].load_markets()
        return self._clients[exchange]

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        if not self._enabled_pairs:
            logger.error("[STARTUP] No trading pairs enabled—check API credentials")
        for pair in self._enabled_pairs:
            key = self._pair_key(pair.exchange, pair.symbol)
            await self._ensure_pair_task(key, pair)
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

    async def _run_pair(self, pair_key: str) -> None:
        cfg = self._pair_configs[pair_key]
        client = await self._client_for(cfg.exchange)
        poller = MarketDataPoller(client, cfg.symbol, interval_s=self._config.settings.poll_interval_s)
        execution = ExecutionManager(client, cfg.symbol)
        state = self._states[pair_key]
        await poller.start()
        try:
            while self._running:
                pair = self._pair_configs[pair_key]
                await self._consume_trades(client, pair, pair_key, state, execution)
                if pair_key not in self._active_pairs:
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
                    self._config.settings,
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
                            order_value=intent.order_value,
                            expected_profit_usd=(intent.order_value * (state.recent_net_edges[-1] / Decimal("10000"))) if state.recent_net_edges else Decimal("0"),
                            reason=intent.reason,
                        )
                    )
                    await execution.sync_quotes(intent)
                else:
                    self._telemetry.skip(pair.exchange, pair.symbol, "planner_rejected")

                await execution.prune_stale_quotes(self._config.settings.stale_order_seconds)
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

    async def _fetch_base_balance(self, client: RestExchangeClient, currency: str) -> Decimal:
        try:
            balance = await client.fetch_balance()
            free = balance.get("free") or {}
            total = balance.get("total") or {}
            raw = free.get(currency, total.get(currency, 0))
            return Decimal(str(raw))
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Failed to fetch base balance for %s: %s", currency, exc)
            return Decimal("0")

    async def _rotation_loop(self) -> None:
        while self._running:
            await asyncio.sleep(max(10.0, self._config.settings.scanner_interval_s))
            snapshots = await self._scanner.refresh()
            self._telemetry.scan(
                snapshots,
                floor_bps=Decimal(self._config.settings.minimum_target_edge_bps),
            )
            snapshot_map = {
                self._pair_key(snap.exchange, snap.symbol): snap for snap in snapshots
            }
            for snapshot in snapshots:
                cfg = self._catalog.register_dynamic(snapshot)
                if cfg:
                    key = self._pair_key(cfg.exchange, cfg.symbol)
                    if key not in self._pair_configs:
                        self._pair_configs[key] = cfg
            ranked = self._score_pairs(snapshot_map)
            allowed: Set[str] = set()
            for _, pair_key in ranked:
                if pair_key not in self._pair_configs:
                    continue
                allowed.add(pair_key)
                if len(allowed) >= self._config.settings.max_active_pairs:
                    break
            for pair_key in allowed:
                cfg = self._pair_configs[pair_key]
                await self._ensure_pair_task(pair_key, cfg)
            if allowed != self._active_pairs:
                logger.info("[ROTATION] Active pairs -> %s", ", ".join(sorted(allowed)))
            self._active_pairs = allowed

    async def _consume_trades(
        self,
        client: RestExchangeClient,
        pair: PairConfig,
        pair_key: str,
        state: PairRuntimeState,
        execution: ExecutionManager,
    ) -> None:
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
            realized, result = self._pnl.process_fill(pair_key, state, side, amount, price, fee_cost)
            if result in {"win", "loss", "flat"}:
                self._risk.register_fill_result(state, result, realized)
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
            if amount > 0:
                await execution.cancel_all_quotes()
                hedge_price = compute_hedge_price(
                    price,
                    side,
                    self._config.settings.hedge_fee_guard_bps,
                    self._config.settings.hedge_buffer_bps,
                )
                if side == "buy":
                    wallet_base = await self._fetch_base_balance(client, pair.base)
                    tracked_base = sum(lot.amount for lot in state.inventory)
                    available_base = min(wallet_base, tracked_base)
                    buffer_multiplier = Decimal("1") - Decimal(self._config.settings.hedge_balance_buffer_bps) / Decimal("10000")
                    if buffer_multiplier < 0:
                        buffer_multiplier = Decimal("0")
                    available_base = (available_base * buffer_multiplier).quantize(Decimal("0.00000001"), rounding=ROUND_DOWN)
                    hedge_amount = min(amount, available_base)
                    hedge_amount = execution.amount_precision(hedge_amount)
                    min_amount = execution.min_order_amount()
                    if min_amount and hedge_amount < min_amount:
                        logger.info(
                            "[HEDGE] skip %s %s amount=%s reason=min_amount",
                            pair.exchange.upper(),
                            pair.symbol,
                            hedge_amount,
                        )
                        continue
                    hedge_notional = hedge_amount * hedge_price
                    if hedge_notional < pair.min_notional_usd:
                        logger.info(
                            "[HEDGE] skip %s %s notional=%s reason=dust",
                            pair.exchange.upper(),
                            pair.symbol,
                            hedge_notional.quantize(Decimal("0.0001")),
                        )
                        continue
                    if hedge_amount > Decimal("0"):
                        placed = await execution.place_hedge(
                            "sell",
                            hedge_amount,
                            hedge_price,
                            allow_taker=False,
                            min_price=hedge_price,
                        )
                        if not placed:
                            await self._handle_failed_hedge(
                                client,
                                execution,
                                pair,
                                state,
                                "sell",
                                hedge_amount,
                                hedge_price,
                            )
                elif side == "sell":
                    stable_balance = await self._fetch_stable_balance(client, pair.quote)
                    max_buy_amount = Decimal("0")
                    if hedge_price > 0 and stable_balance > 0:
                        buffer_multiplier = Decimal("1") - Decimal(self._config.settings.hedge_balance_buffer_bps) / Decimal("10000")
                        if buffer_multiplier < 0:
                            buffer_multiplier = Decimal("0")
                        usable_quote = (stable_balance * buffer_multiplier).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
                        if usable_quote > 0:
                            max_buy_amount = (usable_quote / (hedge_price * Decimal("1.01"))).quantize(Decimal("0.00001"), rounding=ROUND_DOWN)
                    hedge_amount = min(amount, max_buy_amount)
                    hedge_amount = execution.amount_precision(hedge_amount)
                    min_amount = execution.min_order_amount()
                    if min_amount and hedge_amount < min_amount:
                        logger.info(
                            "[HEDGE] skip %s %s amount=%s reason=min_amount",
                            pair.exchange.upper(),
                            pair.symbol,
                            hedge_amount,
                        )
                        continue
                    hedge_notional = hedge_amount * hedge_price
                    if hedge_notional < pair.min_notional_usd:
                        logger.info(
                            "[HEDGE] skip %s %s notional=%s reason=dust",
                            pair.exchange.upper(),
                            pair.symbol,
                            hedge_notional.quantize(Decimal("0.0001")),
                        )
                        continue
                    if hedge_amount > Decimal("0"):
                        allow_taker = realized > 0
                        placed = await execution.place_hedge(
                            "buy",
                            hedge_amount,
                            hedge_price,
                            allow_taker=allow_taker,
                            max_price=hedge_price,
                        )
                        if not placed:
                            await self._handle_failed_hedge(
                                client,
                                execution,
                                pair,
                                state,
                                "buy",
                                hedge_amount,
                                hedge_price,
                            )

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

    async def _ensure_pair_task(self, pair_key: str, pair: PairConfig) -> None:
        self._pair_configs[pair_key] = pair
        if pair_key in self._tasks:
            return
        logger.info(
            "[DISCOVER] starting worker for %s %s", pair.exchange.upper(), pair.symbol
        )
        task = asyncio.create_task(self._run_pair(pair_key))
        self._tasks[pair_key] = task

    async def _handle_failed_hedge(
        self,
        client: RestExchangeClient,
        execution: ExecutionManager,
        pair: PairConfig,
        state: PairRuntimeState,
        side: str,
        amount: Decimal,
        entry_price: Decimal,
    ) -> None:
        now = time.time()
        if state.hedge_failure_ts is None:
            state.hedge_failure_ts = now
            state.hedge_attempt_side = side
            state.last_hedge_entry = entry_price
            state.cooldown_until = max(state.cooldown_until, now + self._config.settings.insufficient_balance_cooldown_s)
            self._telemetry.cooldown(pair.exchange, pair.symbol, state.cooldown_until, "hedge_insufficient")
            return

        elapsed = now - state.hedge_failure_ts
        if elapsed < self._config.settings.hedge_force_flat_seconds:
            return

        best_price = await self._best_price(client, pair.symbol, side)
        if best_price is None:
            return

        min_price = entry_price if side == "sell" else None
        max_price = entry_price if side == "buy" else None
        order_id = await execution.place_hedge(
            side,
            amount,
            best_price,
            allow_taker=True,
            min_price=min_price,
            max_price=max_price,
        )
        if order_id:
            state.hedge_failure_ts = None
            state.hedge_attempt_side = None
            return

        state.cooldown_until = max(state.cooldown_until, now + self._config.settings.insufficient_balance_cooldown_s)
        self._telemetry.cooldown(pair.exchange, pair.symbol, state.cooldown_until, "force_flat_failed")

    async def _best_price(self, client: RestExchangeClient, symbol: str, side: str) -> Optional[Decimal]:
        try:
            book = await client.fetch_order_book(symbol, depth=1)
        except Exception:
            return None
        if side == "sell":
            bids = book.get("bids") or []
            if not bids:
                return None
            return Decimal(str(bids[0][0]))
        asks = book.get("asks") or []
        if not asks:
            return None
        return Decimal(str(asks[0][0]))

    def _score_pairs(self, snapshot_map: Dict[str, PairSnapshot]) -> List[Tuple[float, str]]:
        ranked: List[Tuple[float, str]] = []
        for pair_key, cfg in self._pair_configs.items():
            state = self._states[pair_key]
            snap = snapshot_map.get(pair_key)
            if snap:
                net_edge = snap.net_edge_bps
            elif state.recent_net_edges:
                net_edge = state.recent_net_edges[-1]
            else:
                net_edge = Decimal("-500")
            stats = self._pnl.get_stats(pair_key)
            penalty = Decimal(stats.losses * 20 + state.skip_reasons.get("edge_target", 0) * 5)
            if len(state.recent_realized) >= self._config.settings.negative_fill_lookback:
                window = list(state.recent_realized)[-self._config.settings.negative_fill_lookback:]
                if window and all(value <= 0 for value in window):
                    penalty += Decimal("300")
            score = float(net_edge - penalty)
            ranked.append((score, pair_key))
        ranked.sort(reverse=True, key=lambda item: item[0])
        return ranked

    def _pair_key(self, exchange: str, symbol: str) -> str:
        return f"{exchange}:{symbol}"
