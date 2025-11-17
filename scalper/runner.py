from __future__ import annotations

import asyncio
import contextlib
import logging
import random
import time
from collections import defaultdict
from decimal import Decimal, ROUND_DOWN
from typing import Dict, Sequence, Set, Optional, List, Tuple, Callable, Awaitable

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


class BalanceCache:
    """Cache for balance data with TTL to reduce API calls."""
    
    def __init__(self, ttl_s: float = 3.0):
        self._cache: Dict[str, Tuple[Decimal, float]] = {}
        self._ttl_s = ttl_s
        self._lock = asyncio.Lock()
    
    async def get(
        self, 
        client: RestExchangeClient, 
        currency: str,
        fetch_func: Callable[[RestExchangeClient, str], Awaitable[Decimal]]
    ) -> Decimal:
        """Get balance from cache or fetch fresh if expired."""
        cache_key = f"{client._id}:{currency}"
        async with self._lock:
            if cache_key in self._cache:
                balance, timestamp = self._cache[cache_key]
                if time.time() - timestamp < self._ttl_s:
                    return balance
            # Fetch fresh balance
            balance = await fetch_func(client, currency)
            self._cache[cache_key] = (balance, time.time())
            return balance
    
    def invalidate(self, exchange: str, currency: Optional[str] = None) -> None:
        """Invalidate cache for a specific exchange/currency."""
        if currency:
            cache_key = f"{exchange}:{currency}"
            self._cache.pop(cache_key, None)
        else:
            # Invalidate all for this exchange
            keys_to_remove = [k for k in self._cache.keys() if k.startswith(f"{exchange}:")]
            for key in keys_to_remove:
                self._cache.pop(key, None)


class CircuitBreaker:
    """Circuit breaker pattern to temporarily disable failing exchanges."""
    
    def __init__(self, failure_threshold: int = 5, timeout: float = 60.0):
        self._failures = 0
        self._failure_threshold = failure_threshold
        self._timeout = timeout
        self._opened_at: Optional[float] = None
        self._state = "closed"  # closed, open, half_open
        self._lock = asyncio.Lock()
    
    async def record_success(self) -> None:
        async with self._lock:
            self._failures = 0
            self._state = "closed"
            self._opened_at = None
    
    async def record_failure(self) -> None:
        async with self._lock:
            self._failures += 1
            if self._failures >= self._failure_threshold:
                self._state = "open"
                self._opened_at = time.time()
                logger.warning(
                    "[CIRCUIT] Circuit breaker opened after %s failures (timeout=%ss)",
                    self._failures,
                    self._timeout,
                )
    
    async def can_proceed(self) -> bool:
        async with self._lock:
            if self._state == "closed":
                return True
            if self._state == "open":
                if self._opened_at and time.time() - self._opened_at > self._timeout:
                    self._state = "half_open"
                    logger.info("[CIRCUIT] Circuit breaker entering half-open state")
                    return True
                return False
            return True  # half_open
    
    async def is_open(self) -> bool:
        async with self._lock:
            return self._state == "open"


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
        self._pnl_task: Optional[asyncio.Task[None]] = None
        self._running = False
        self._enabled_pairs = self._filter_pairs(config.pairs)
        self._active_pairs: Set[str] = set()
        # Performance improvements
        self._balance_cache = BalanceCache(ttl_s=3.0)
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}

    async def _client_for(self, exchange: str) -> RestExchangeClient:
        # Check circuit breaker
        if exchange not in self._circuit_breakers:
            self._circuit_breakers[exchange] = CircuitBreaker(failure_threshold=5, timeout=60.0)
        breaker = self._circuit_breakers[exchange]
        if await breaker.is_open():
            if not await breaker.can_proceed():
                raise RuntimeError(f"Circuit breaker open for {exchange}")
        
        if exchange not in self._clients:
            creds_data = self._config.venue_keys.get(exchange)
            if not creds_data:
                raise RuntimeError(f"Missing credentials for {exchange}")
            api_key = creds_data.get("api_key", "").strip()
            api_secret = creds_data.get("api_secret", "").strip()
            if not api_key or not api_secret:
                raise RuntimeError(f"Invalid credentials for {exchange}: key or secret is empty")
            creds = ExchangeCredentials(
                api_key=api_key,
                api_secret=api_secret,
                passphrase=creds_data.get("passphrase"),
            )
            try:
                self._clients[exchange] = RestExchangeClient(exchange, creds)
                logger.info("[STARTUP] Initializing %s client...", exchange.upper())
                await self._clients[exchange].load_markets()
                markets = getattr(self._clients[exchange]._client, "markets", {})  # type: ignore[attr-defined]
                logger.info("[STARTUP] %s loaded %s markets", exchange.upper(), len(markets))
                await breaker.record_success()
            except Exception as exc:
                logger.error("[STARTUP] Failed to initialize %s client: %s", exchange.upper(), exc, exc_info=True)
                await breaker.record_failure()
                raise
        return self._clients[exchange]

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        if not self._enabled_pairs:
            logger.error("[STARTUP] No trading pairs enabled—check API credentials")
        # Seed configs for enabled pairs; tasks will spin up when rotation activates them.
        for pair in self._enabled_pairs:
            key = self._pair_key(pair.exchange, pair.symbol)
            self._pair_configs[key] = pair
        await self._run_rotation_step(initial=True)
        self._rotation_task = asyncio.create_task(self._rotation_loop())
        self._pnl_task = asyncio.create_task(self._pnl_summary_loop())

    async def stop(self) -> None:
        self._running = False
        await asyncio.gather(*self._tasks.values(), return_exceptions=True)
        self._tasks.clear()
        if self._rotation_task:
            self._rotation_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._rotation_task
            self._rotation_task = None
        if self._pnl_task:
            self._pnl_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._pnl_task
            self._pnl_task = None
        await asyncio.gather(*(client.close() for client in self._clients.values()), return_exceptions=True)

    async def _run_pair(self, pair_key: str) -> None:
        cfg = self._pair_configs[pair_key]
        client = await self._client_for(cfg.exchange)
        poller = MarketDataPoller(
            client,
            cfg.symbol,
            self._config.settings,
            interval_s=self._config.settings.poll_interval_s,
        )
        execution = ExecutionManager(client, cfg.symbol, self._config.settings)
        state = self._states[pair_key]
        await poller.start()
        try:
            while self._running:
                pair = self._pair_configs[pair_key]
                # Aggressively sweep stale/orphan exchange orders before any planning/sizing
                await execution.sweep_orphans(force_age_cancel_s=90.0)
                await self._consume_trades(client, pair, pair_key, state, execution)
                
                # CRITICAL: Sweep for orphaned inventory (crypto without sell orders)
                # This ensures we never have crypto sitting in the account unprotected
                try:
                    wallet_base = await self._fetch_base_balance(client, pair.base)
                    tracked_base = sum(lot.amount for lot in state.inventory)
                    if wallet_base > 0:
                        # Calculate min_price for protective sell (entry + fees)
                        hedge_price = None
                        if state.inventory:
                            # Use the most recent inventory lot's price as entry
                            entry_price = state.inventory[-1].price  # Most recent entry
                            hedge_price = compute_hedge_price(
                                entry_price,
                                "buy",  # We bought, so we need to sell
                                self._config.settings.hedge_fee_guard_bps,
                                self._config.settings.hedge_buffer_bps,
                            )
                        else:
                            # Fallback: use current market price if we have crypto but no inventory tracking
                            # This handles edge cases where crypto exists but wasn't properly tracked
                            snapshot = poller.latest()
                            if snapshot and snapshot.best_bid > 0:
                                # Use current bid price as a conservative estimate
                                # Add fees to ensure we're at least break-even
                                hedge_price = snapshot.best_bid * (
                                    Decimal("1") + 
                                    Decimal(self._config.settings.hedge_fee_guard_bps) / Decimal("10000") +
                                    Decimal(self._config.settings.hedge_buffer_bps) / Decimal("10000")
                                )
                                logger.warning(
                                    "[SWEEPER] %s %s: Found %s %s in wallet but no inventory tracking! Using market price %s as fallback",
                                    pair.exchange.upper(),
                                    pair.symbol,
                                    wallet_base,
                                    pair.base,
                                    hedge_price,
                                )
                        
                        if hedge_price and hedge_price > 0:
                            await execution.sweep_orphaned_inventory(
                                wallet_base,
                                tracked_base,
                                hedge_price,
                                pair.min_notional_usd,
                            )
                except Exception as exc:
                    logger.debug("[SWEEPER] Error sweeping orphaned inventory for %s %s: %s", pair.exchange.upper(), pair.symbol, exc)
                
                if pair_key not in self._active_pairs:
                    await execution.cancel_all_quotes()
                    await execution.prune_stale_hedges(self._config.settings.hedge_stage_one_seconds)
                    await asyncio.sleep(self._config.settings.poll_interval_s)
                    continue
                snapshot = poller.latest()
                if not snapshot:
                    await execution.sweep_orphans(force_age_cancel_s=90.0)
                    await asyncio.sleep(self._config.settings.poll_interval_s)
                    continue
                # Batch-cancel both sides immediately if spread collapses
                try:
                    if snapshot.spread_bps < (Decimal(pair.min_spread_bps) / Decimal("2")):
                        await execution.cancel_all_quotes()
                        await asyncio.sleep(self._config.settings.poll_interval_s)
                        continue
                except Exception:
                    pass
                stable_balance = await self._fetch_stable_balance(client, pair.quote)
                logger.debug(
                    "[BALANCE] %s %s quote=%s balance=%s",
                    pair.exchange.upper(),
                    pair.symbol,
                    pair.quote,
                    stable_balance.quantize(Decimal("0.01")),
                )
                assessment = self._risk.evaluate(pair, state, stable_balance)
                if not assessment.allowed:
                    logger.info(
                        "[RISK] Skip %s %s reason=%s balance=%s",
                        pair.exchange.upper(),
                        pair.symbol,
                        assessment.reason,
                        stable_balance.quantize(Decimal("0.01")),
                    )
                    await execution.sweep_orphans(force_age_cancel_s=90.0)
                    await execution.cancel_all_quotes()
                    await execution.prune_stale_hedges(self._config.settings.hedge_stage_one_seconds)
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
                    # Invalidate balance cache after placing orders
                    self._balance_cache.invalidate(pair.exchange)
                else:
                    self._telemetry.skip(pair.exchange, pair.symbol, "planner_rejected")

                await execution.prune_stale_quotes(self._config.settings.stale_order_seconds)
                await execution.prune_stale_hedges(self._config.settings.hedge_stage_one_seconds)
                await asyncio.sleep(self._config.settings.poll_interval_s)
        finally:
            await poller.stop()
            await execution.cancel_all()

    async def _fetch_stable_balance(self, client: RestExchangeClient, currency: str) -> Decimal:
        """Fetch available stable currency balance (USD, USDC, etc.) for trading."""
        async def _fetch_impl(c: RestExchangeClient, curr: str) -> Decimal:
            try:
                balance = await c.fetch_balance()
                if not balance:
                    logger.warning("[BALANCE] Empty balance response for %s", curr)
                    return Decimal("0")
                # Prefer 'free' (available) over 'total' (including locked)
                free = balance.get("free") or {}
                total = balance.get("total") or {}
                # Try free first, fallback to total
                amount = free.get(curr) or total.get(curr) or 0
                amount = Decimal(str(amount))
                if amount < 0:
                    logger.warning("[BALANCE] Negative balance for %s: %s", curr, amount)
                    return Decimal("0")
                return amount
            except Exception as exc:  # pragma: no cover - defensive
                logger.error("[BALANCE] Failed to fetch balance for %s: %s", curr, exc, exc_info=True)
                return Decimal("0")
        
        return await self._balance_cache.get(client, currency, _fetch_impl)

    async def _fetch_base_balance(self, client: RestExchangeClient, currency: str) -> Decimal:
        """Fetch available base currency balance (BTC, ETH, etc.) for hedging."""
        async def _fetch_impl(c: RestExchangeClient, curr: str) -> Decimal:
            try:
                balance = await c.fetch_balance()
                if not balance:
                    logger.warning("[BALANCE] Empty balance response for %s", curr)
                    return Decimal("0")
                free = balance.get("free") or {}
                total = balance.get("total") or {}
                # Prefer free (available) balance for hedging
                raw = free.get(curr) or total.get(curr) or 0
                amount = Decimal(str(raw))
                if amount < 0:
                    logger.warning("[BALANCE] Negative base balance for %s: %s", curr, amount)
                    return Decimal("0")
                return amount
            except Exception as exc:  # pragma: no cover - defensive
                logger.error("[BALANCE] Failed to fetch base balance for %s: %s", curr, exc, exc_info=True)
                return Decimal("0")
        
        return await self._balance_cache.get(client, currency, _fetch_impl)
    
    async def _fetch_balances(
        self, client: RestExchangeClient, pair: PairConfig
    ) -> Tuple[Decimal, Decimal]:
        """Fetch both base and quote balances concurrently."""
        base_task = self._fetch_base_balance(client, pair.base)
        quote_task = self._fetch_stable_balance(client, pair.quote)
        base_bal, quote_bal = await asyncio.gather(base_task, quote_task)
        return base_bal, quote_bal

    async def _rotation_loop(self) -> None:
        interval = max(10.0, self._config.settings.scanner_interval_s)
        while self._running:
            await asyncio.sleep(interval)
            await self._run_rotation_step()

    async def _pnl_summary_loop(self) -> None:
        """Emit cumulative PnL/win-rate stats per pair every 2 minutes."""
        interval = 120.0  # 2 minutes instead of 5
        while self._running:
            await asyncio.sleep(interval)
            try:
                total_realized = Decimal("0")
                total_fees = Decimal("0")
                total_trades = 0
                total_wins = 0
                total_losses = 0
                total_flats = 0
                
                # Log per-pair stats
                for pair_key, state in self._states.items():
                    stats = self._pnl.get_stats(pair_key)
                    if stats.trades == 0:
                        continue
                    
                    win_rate_pct = (
                        (Decimal(stats.wins) / Decimal(stats.trades) * Decimal("100")).quantize(Decimal("0.01"))
                        if stats.trades > 0
                        else Decimal("0")
                    )
                    net_profit = stats.realized - stats.fees
                    
                    total_realized += stats.realized
                    total_fees += stats.fees
                    total_trades += stats.trades
                    total_wins += stats.wins
                    total_losses += stats.losses
                    total_flats += stats.flats
                    
                    logger.info(
                        "[PNL_SUMMARY] %s realized=%s fees=%s net_profit=%s wins=%s losses=%s flats=%s trades=%s win_rate=%s%%",
                        pair_key,
                        stats.realized.quantize(Decimal("0.0001")),
                        stats.fees.quantize(Decimal("0.0001")),
                        net_profit.quantize(Decimal("0.0001")),
                        stats.wins,
                        stats.losses,
                        stats.flats,
                        stats.trades,
                        win_rate_pct,
                    )
                
                # Log overall summary across all pairs
                if total_trades > 0:
                    overall_win_rate = (Decimal(total_wins) / Decimal(total_trades) * Decimal("100")).quantize(Decimal("0.01"))
                    overall_net_profit = total_realized - total_fees
                    logger.info(
                        "[PNL_OVERALL] TOTAL realized=%s fees=%s net_profit=%s wins=%s losses=%s flats=%s trades=%s win_rate=%s%%",
                        total_realized.quantize(Decimal("0.0001")),
                        total_fees.quantize(Decimal("0.0001")),
                        overall_net_profit.quantize(Decimal("0.0001")),
                        total_wins,
                        total_losses,
                        total_flats,
                        total_trades,
                        overall_win_rate,
                    )
            except Exception as exc:
                logger.error("[PNL_SUMMARY] Error generating summary: %s", exc, exc_info=True)
                continue

    async def _run_rotation_step(self, *, initial: bool = False) -> None:
        snapshots = await self._scanner.refresh()
        self._telemetry.scan(
            snapshots,
            floor_bps=Decimal(self._config.settings.minimum_target_edge_bps),
        )
        snapshot_map: Dict[str, PairSnapshot] = {}
        for snapshot in snapshots:
            key = self._pair_key(snapshot.exchange, snapshot.symbol)
            snapshot_map[key] = snapshot
            cfg = self._catalog.register_dynamic(snapshot)
            if cfg and key not in self._pair_configs:
                self._pair_configs[key] = cfg

        # Group snapshots by exchange for per-exchange ranking
        snapshots_by_exchange: Dict[str, List[PairSnapshot]] = {}
        for snapshot in snapshots:
            exchange = snapshot.exchange.lower()
            if exchange not in snapshots_by_exchange:
                snapshots_by_exchange[exchange] = []
            snapshots_by_exchange[exchange].append(snapshot)

        # Rank pairs per exchange and select top N from each
        allowed: Set[str] = set()
        all_ranked: List[Tuple[float, str]] = []
        max_per_exchange = 5  # Top 5 per exchange
        
        for exchange, exchange_snapshots in snapshots_by_exchange.items():
            exchange_ranked = self._score_pairs(exchange_snapshots)
            all_ranked.extend(exchange_ranked)
            
            logger.info(
                "[ROTATION] %s ranked %s pairs, selecting top %s",
                exchange.upper(),
                len(exchange_ranked),
                min(max_per_exchange, len(exchange_ranked)),
            )
            
            # Select top N pairs from this exchange
            exchange_count = 0
            for _, pair_key in exchange_ranked:
                if exchange_count >= max_per_exchange:
                    break
                snapshot = snapshot_map.get(pair_key)
                if not snapshot:
                    continue
                if snapshot.score <= 0:
                    continue
                cfg = self._pair_configs.get(pair_key)
                if cfg is None:
                    cfg = self._catalog.get_by_key(pair_key)
                    if cfg:
                        self._pair_configs[pair_key] = cfg
                if cfg is None:
                    continue
                await self._ensure_pair_task(pair_key, cfg)
                allowed.add(pair_key)
                exchange_count += 1
                
            if exchange_count > 0:
                selected_pairs = [pair_key for _, pair_key in exchange_ranked[:exchange_count]]
                logger.info(
                    "[ROTATION] %s selected: %s",
                    exchange.upper(),
                    ", ".join(selected_pairs),
                )

        if not allowed:
            if initial or self._active_pairs:
                logger.info("[ROTATION] No markets cleared thresholds; parking all pairs")
        elif allowed != self._active_pairs:
            logger.info("[ROTATION] Active pairs -> %s", ", ".join(sorted(allowed)))

        self._active_pairs = allowed
        # Sort all_ranked for telemetry (combined view)
        all_ranked.sort(reverse=True, key=lambda item: item[0])
        self._telemetry.rotation(sorted(self._active_pairs), all_ranked, self._states)

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
            meta = execution.mark_filled(order_ref or trade_id)
            if meta and meta.get("tag") in {"hedge", "hedge_taker"}:
                expected_price = Decimal(str(meta.get("price", price))) if meta.get("price") else price
                slip_bps = Decimal("0")
                if expected_price > 0:
                    slip_bps = ((price - expected_price) / expected_price) * Decimal("10000")
                logger.info(
                    "[SLIP] %s %s side=%s expected=%s fill=%s slip_bps=%s stage=%s",
                    pair.exchange.upper(),
                    pair.symbol,
                    side,
                    expected_price,
                    price,
                    slip_bps.quantize(Decimal("0.01")),
                    meta.get("stage", 0),
                )
            start_ts = float(trade.get("datetime_ms") or trade.get("timestamp") or time.time() * 1000)
            latency_ms = max(0.0, time.time() * 1000 - start_ts)
            realized, result = self._pnl.process_fill(pair_key, state, side, amount, price, fee_cost)
            if result in {"win", "loss", "flat"}:
                self._risk.register_fill_result(state, result, realized)
                state.update_probe(
                    success=result == "win",
                    cfg_base=pair.base_probe_size_usd,
                    cfg_step=pair.probe_step_usd,
                    cfg_max=pair.max_probe_size_usd,
                )
                state.register_fill(result, latency_ms, realized)
            if realized != 0:
                stats = self._pnl.get_stats(pair_key)
                win_rate_pct = (
                    (Decimal(stats.wins) / Decimal(stats.trades) * Decimal("100")).quantize(Decimal("0.01"))
                    if stats.trades > 0
                    else Decimal("0")
                )
                net_profit = stats.realized - stats.fees
                logger.info(
                    "[FILL] %s %s side=%s amount=%s price=%s realized=%s result=%s win_rate=%s%% net_profit=%s trades=%s",
                    pair.exchange.upper(),
                    pair.symbol,
                    side,
                    amount,
                    price,
                    realized.quantize(Decimal("0.0001")),
                    result.upper(),
                    win_rate_pct,
                    net_profit.quantize(Decimal("0.0001")),
                    stats.trades,
                )
            if amount > 0:
                # Invalidate balance cache after a fill
                self._balance_cache.invalidate(pair.exchange)
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
                        await self._flatten_dust(
                            execution,
                            client,
                            pair,
                            state,
                            side="sell",
                            remaining=available_base,
                            price=hedge_price,
                            reason="min_amount",
                        )
                        continue
                    hedge_notional = hedge_amount * hedge_price
                    if hedge_notional < pair.min_notional_usd:
                        await self._flatten_dust(
                            execution,
                            client,
                            pair,
                            state,
                            side="sell",
                            remaining=available_base,
                            price=hedge_price,
                            reason="dust",
                        )
                        continue
                    if hedge_amount > Decimal("0"):
                        try:
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
                        except Exception as exc:
                            logger.error(
                                "[HEDGE] Exception placing sell hedge for %s %s amount=%s price=%s: %s",
                                pair.exchange.upper(),
                                pair.symbol,
                                hedge_amount,
                                hedge_price,
                                exc,
                                exc_info=True,
                            )
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
                        await self._flatten_dust(
                            execution,
                            client,
                            pair,
                            state,
                            side="buy",
                            remaining=max_buy_amount,
                            price=hedge_price,
                            reason="min_amount",
                        )
                        continue
                    hedge_notional = hedge_amount * hedge_price
                    if hedge_notional < pair.min_notional_usd:
                        await self._flatten_dust(
                            execution,
                            client,
                            pair,
                            state,
                            side="buy",
                            remaining=max_buy_amount,
                            price=hedge_price,
                            reason="dust",
                        )
                        continue
                    if hedge_amount > Decimal("0"):
                        allow_taker = realized > 0
                        try:
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
                        except Exception as exc:
                            logger.error(
                                "[HEDGE] Exception placing buy hedge for %s %s amount=%s price=%s: %s",
                                pair.exchange.upper(),
                                pair.symbol,
                                hedge_amount,
                                hedge_price,
                                exc,
                                exc_info=True,
                            )
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
        try:
            order_id = await execution.place_hedge(
                side,
                amount,
                best_price,
                allow_taker=True,
                min_price=min_price,
                max_price=max_price,
            )
        except Exception as exc:
            logger.error(
                "[HEDGE] Exception in force-flat hedge for %s %s %s amount=%s price=%s: %s",
                pair.exchange.upper(),
                pair.symbol,
                side.upper(),
                amount,
                best_price,
                exc,
                exc_info=True,
            )
            order_id = None
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
            if not bids or len(bids) == 0:
                return None
            try:
                price = Decimal(str(bids[0][0]))
                if price <= 0:
                    return None
                return price
            except (IndexError, ValueError, TypeError):
                return None
        asks = book.get("asks") or []
        if not asks or len(asks) == 0:
            return None
        try:
            price = Decimal(str(asks[0][0]))
            if price <= 0:
                return None
            return price
        except (IndexError, ValueError, TypeError):
            return None

    def _score_pairs(self, snapshots: Sequence[PairSnapshot]) -> List[Tuple[float, str]]:
        ranked: List[Tuple[float, str]] = []
        for snapshot in snapshots:
            pair_key = self._pair_key(snapshot.exchange, snapshot.symbol)
            state = self._states[pair_key]
            net_edge = snapshot.net_edge_bps
            stats = self._pnl.get_stats(pair_key)
            penalty = Decimal(stats.losses * 15 + state.skip_reasons.get("edge_target", 0) * 5)

            fill_total = max(state.fill_count, 0)
            win_rate = Decimal("0")
            if fill_total > 0:
                win_rate = Decimal(state.win_count) / Decimal(fill_total)

            if fill_total >= 5 and win_rate < Decimal("0.35"):
                continue

            recent_window = list(state.recent_realized)[-self._config.settings.negative_fill_lookback :]
            if recent_window and all(val <= 0 for val in recent_window):
                penalty += Decimal("200")

            fill_prob = Decimal("0")
            if fill_total > 0:
                skip_penalty = (
                    state.skip_reasons.get("edge_floor", 0)
                    + state.skip_reasons.get("edge_target", 0)
                    + state.skip_reasons.get("no_depth", 0)
                    + 1
                )
                fill_prob = Decimal(fill_total) / Decimal(fill_total + skip_penalty)

            tier_edge = Decimal("0")
            if state.current_tier and state.current_tier in state.tier_scores:
                tier_edge = state.tier_scores[state.current_tier]

            score_core = net_edge + tier_edge
            score_modifier = Decimal("0.5")
            if fill_prob > 0:
                score_modifier += fill_prob / Decimal("2")
            if win_rate > 0:
                score_modifier += win_rate / Decimal("3")

            score_value = float(score_core * score_modifier) + float(snapshot.score) / 1000
            score_value -= float(penalty)
            if stats.realized < 0:
                score_value += float(stats.realized)

            time_since_fill = time.time() - state.last_fill_ts if state.last_fill_ts else None
            if time_since_fill and time_since_fill > 900:
                score_value *= 0.7

            ranked.append((float(score_value), pair_key))
        ranked.sort(reverse=True, key=lambda item: item[0])
        return ranked

    async def _flatten_dust(
        self,
        execution: ExecutionManager,
        client: RestExchangeClient,
        pair: PairConfig,
        state: PairRuntimeState,
        *,
        side: str,
        remaining: Decimal,
        price: Decimal,
        reason: str,
    ) -> None:
        """Force-flatten small residual inventory so risk guards clear."""
        if remaining <= 0:
            return
        min_amount = execution.min_order_amount()
        if min_amount and remaining < min_amount:
            cleared = self._clear_small_inventory(state, pair.min_notional_usd)
            if cleared:
                logger.info(
                    "[HEDGE] drop_dust %s %s remaining=%s reason=%s",
                    pair.exchange.upper(),
                    pair.symbol,
                    remaining,
                    reason,
                )
            return
        best_price = await self._best_price(client, pair.symbol, side)
        if best_price is None:
            best_price = price
        order_id = await execution.flatten_inventory(side, remaining, best_price)
        if order_id:
            logger.info(
                "[HEDGE] force_flat %s %s remaining=%s reason=%s",
                pair.exchange.upper(),
                pair.symbol,
                remaining,
                reason,
            )
            state.hedge_failure_ts = time.time()
        else:
            cleared = self._clear_small_inventory(state, pair.min_notional_usd)
            if cleared:
                logger.info(
                    "[HEDGE] drop_dust %s %s remaining=%s reason=%s",
                    pair.exchange.upper(),
                    pair.symbol,
                    remaining,
                    reason,
                )

    @staticmethod
    def _clear_small_inventory(state: PairRuntimeState, min_notional: Decimal) -> bool:
        changed = False
        while state.inventory and (state.inventory[0].amount * state.inventory[0].price) < min_notional:
            state.inventory.popleft()
            changed = True
        return changed

    def _pair_key(self, exchange: str, symbol: str) -> str:
        return f"{exchange}:{symbol}"
