from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Awaitable, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from .config import PairConfig, ScalperConfig, EngineSettings
from .edge_utils import estimate_slippage_bps
from .exchange import RestExchangeClient

logger = logging.getLogger(__name__)


@dataclass
class PairSnapshot:
    exchange: str
    symbol: str
    base: str
    quote: str
    spread_bps: Decimal
    gross_edge_bps: Decimal
    slippage_bps: Decimal
    fees_bps: Decimal
    net_edge_bps: Decimal
    effective_edge_bps: Decimal
    depth_usd: Decimal
    top_bid_depth_usd: Decimal
    top_ask_depth_usd: Decimal
    maker_fee_bps: Decimal
    taker_fee_bps: Decimal
    volume_usd: Decimal
    volume_known: bool
    marker: str
    reason: str
    order_value_usd: Decimal
    avg_bid: Decimal
    avg_ask: Decimal
    score: Decimal
    timestamp: float


class OpportunityScanner:
    """Scans exchanges for high-edge scalping candidates."""

    def __init__(self, config: ScalperConfig, client_getter: Callable[[str], Awaitable[RestExchangeClient]]) -> None:
        self._config = config
        self._client_getter = client_getter
        self._snapshots: Dict[str, PairSnapshot] = {}
        self._lock = asyncio.Lock()

    async def refresh(self) -> List[PairSnapshot]:
        async with self._lock:
            results: List[PairSnapshot] = []
            exchanges = list(self._config.venue_keys.keys())
            logger.info("[SCAN] Starting refresh for exchanges: %s", ", ".join(ex.upper() for ex in exchanges))
            for venue in exchanges:
                try:
                    client = await self._client_getter(venue)
                except Exception as exc:
                    logger.warning("[SCAN] unable to init client for %s: %s", venue.upper(), exc)
                    continue
                markets = getattr(client._client, "markets", {})  # type: ignore[attr-defined]
                if not markets:
                    try:
                        logger.info("[SCAN] Loading markets for %s...", venue.upper())
                        await client.load_markets()
                        markets = getattr(client._client, "markets", {})  # type: ignore[attr-defined]
                        logger.info("[SCAN] %s loaded %s markets", venue.upper(), len(markets))
                    except Exception as exc:  # pragma: no cover - defensive
                        logger.error("[SCAN] load_markets failed for %s: %s", venue.upper(), exc, exc_info=True)
                        continue
                if not markets:
                    logger.error("[SCAN] %s markets dict is empty after load - check API credentials and network", venue.upper())
                    continue
                logger.info("[SCAN] %s has %s markets available", venue.upper(), len(markets))
                candidates = self._select_markets(markets, venue)
                logger.info("[SCAN] %s selected %s markets to evaluate", venue.upper(), len(candidates))
                kept_local = 0
                evaluated_count = 0
                for symbol in candidates:
                    snapshot = await self._evaluate_market(venue, symbol, client)
                    evaluated_count += 1
                    if snapshot:
                        key = f"{venue}:{symbol}"
                        self._snapshots[key] = snapshot
                        results.append(snapshot)
                        kept_local += 1
                logger.info(
                    "[SCAN] %s evaluated=%s kept=%s",
                    venue.upper(),
                    evaluated_count,
                    kept_local,
                )
            # Keep most recent snapshot for any market not refreshed this pass
            results.extend(value for key, value in self._snapshots.items() if value not in results)
            results.sort(key=lambda snap: (snap.score, snap.net_edge_bps), reverse=True)
            return results

    def _select_markets(self, markets: Dict[str, Dict], venue: str) -> Sequence[str]:
        allowed_quotes = set(self._config.settings.scanner_quote_currencies)
        # Normalize quote currencies to uppercase for case-insensitive matching
        allowed_quotes_normalized = {q.upper() for q in allowed_quotes}
        filtered = []
        skipped_inactive = 0
        skipped_quote = 0
        seen_quotes: Dict[str, int] = {}
        sample_symbols: List[str] = []
        sample_active_values: List[Any] = []
        
        # For Gemini, be more lenient with active check - some markets may not have this field set correctly
        is_gemini = venue.lower() == "gemini"
        
        def _extract_base_quote(symbol: str, meta: Dict) -> Tuple[Optional[str], Optional[str]]:
            """Extract base and quote from metadata or symbol."""
            base = meta.get("base")
            quote = meta.get("quote")
            if base and quote:
                return base, quote
            # Normalize symbol to uppercase for matching
            symbol_upper = symbol.upper()
            # Try to extract from symbol (e.g., "BTC/USD" or "BTCUSD")
            if "/" in symbol:
                parts = symbol.split("/")
                if len(parts) == 2:
                    return parts[0].upper(), parts[1].upper()
            # Try common patterns for Gemini (e.g., "BTCUSD", "ETHUSD")
            # Check against allowed quotes in order of length (longest first) to avoid partial matches
            sorted_quotes = sorted(allowed_quotes, key=len, reverse=True)
            for allowed_quote in sorted_quotes:
                quote_upper = allowed_quote.upper()
                if symbol_upper.endswith(quote_upper):
                    base_part = symbol_upper[:-len(quote_upper)]
                    if base_part and len(base_part) >= 2:  # Minimum base length
                        return base_part, allowed_quote.upper()
            return None, None
        
        for symbol, meta in markets.items():
            if len(sample_symbols) < 10:
                sample_symbols.append(symbol)
                active_val = meta.get("active")
                if active_val not in sample_active_values:
                    sample_active_values.append(active_val)
            
            # Check active status - for Gemini, be more lenient
            # Gemini markets may have 'active' field set incorrectly, so we check if market has required fields instead
            if is_gemini:
                # For Gemini: extract base/quote from metadata or symbol
                base, quote = _extract_base_quote(symbol, meta)
                has_required = bool(base and quote)
                active = meta.get("active")
                # Only skip if explicitly marked inactive AND we can't determine base/quote
                if active is False and not has_required:
                    skipped_inactive += 1
                    continue
                # If we can't determine base/quote from symbol either, skip
                if not has_required:
                    skipped_inactive += 1
                    continue
                # Use extracted quote for matching
                quote_to_check = quote
            else:
                # Other exchanges: default to True if missing
                if not meta.get("active", True):
                    skipped_inactive += 1
                    continue
                quote_to_check = meta.get("quote")
            
            # Use extracted quote for Gemini, metadata quote for others
            if quote_to_check:
                seen_quotes[quote_to_check] = seen_quotes.get(quote_to_check, 0) + 1
            # Case-insensitive quote matching
            quote_normalized = quote_to_check.upper() if quote_to_check else ""
            if quote_normalized not in allowed_quotes_normalized:
                skipped_quote += 1
                continue
            filtered.append((meta.get("info", {}).get("volume") or meta.get("info", {}).get("baseVolume") or 0, symbol))
        filtered.sort(reverse=True, key=lambda item: float(item[0]) if item[0] is not None else 0.0)
        limit = self._config.settings.scanner_max_markets
        result = [symbol for _, symbol in filtered[:limit]]
        top_quotes = sorted(seen_quotes.items(), key=lambda x: x[1], reverse=True)[:5]
        logger.info(
            "[SCAN] market selection: total=%s active=%s quote_match=%s selected=%s (inactive_skipped=%s quote_skipped=%s allowed_quotes=%s top_quotes=%s sample_symbols=%s sample_active=%s)",
            len(markets),
            len(markets) - skipped_inactive,
            len(filtered),
            len(result),
            skipped_inactive,
            skipped_quote,
            sorted(allowed_quotes),
            top_quotes,
            sample_symbols,
            sample_active_values[:5],
        )
        if len(result) == 0 and len(markets) > 0:
            # Show more diagnostic info for Gemini
            sample_quotes = {}
            sample_meta = {}
            for s in sample_symbols[:20]:
                meta = markets.get(s, {})
                sample_quotes[s] = meta.get("quote", "N/A")
                # Show sample metadata structure for debugging
                sample_meta[s] = {
                    "base": meta.get("base", "N/A"),
                    "quote": meta.get("quote", "N/A"),
                    "active": meta.get("active", "N/A"),
                    "symbol": s,
                }
            all_quotes = set()
            for s in list(markets.keys())[:50]:
                meta = markets.get(s, {})
                quote = meta.get("quote")
                if quote:
                    all_quotes.add(quote)
                # Also try extracting from symbol
                base, quote_extracted = _extract_base_quote(s, meta)
                if quote_extracted:
                    all_quotes.add(quote_extracted)
            logger.error(
                "[SCAN] %s: No markets selected! Check quote currencies.\n"
                "  Allowed quotes: %s\n"
                "  Sample market quotes: %s\n"
                "  Sample metadata: %s\n"
                "  Unique quotes in markets: %s",
                venue.upper(),
                sorted(allowed_quotes),
                sample_quotes,
                sample_meta,
                sorted(all_quotes),
            )
        return result

    async def _evaluate_market(
        self,
        exchange: str,
        symbol: str,
        client: RestExchangeClient,
    ) -> Optional[PairSnapshot]:
        try:
            book = await client.fetch_order_book(symbol, depth=5)
        except Exception as exc:
            self._log_candidate(
                exchange,
                symbol,
                "FETCH_ERROR",
                Decimal("0"),
                Decimal("0"),
                Decimal("0"),
                Decimal("0"),
                Decimal("0"),
                "order_book",
                details=str(exc),
            )
            return None

        bids = book.get("bids") or []
        asks = book.get("asks") or []
        if not bids or not asks:
            logger.debug("[SCAN] %s %s: empty order book", exchange.upper(), symbol)
            return None

        best_bid_price = Decimal(str(bids[0][0]))
        best_ask_price = Decimal(str(asks[0][0]))
        if best_bid_price <= 0 or best_ask_price <= 0 or best_ask_price <= best_bid_price:
            logger.debug("[SCAN] %s %s: invalid prices bid=%s ask=%s", exchange.upper(), symbol, best_bid_price, best_ask_price)
            return None

        settings = self._config.settings

        total_bid_value = self._total_value(bids)
        total_ask_value = self._total_value(asks)
        book_value = min(total_bid_value, total_ask_value)
        if book_value <= 0:
            self._log_candidate(
                exchange,
                symbol,
                "RED_X",
                Decimal("0"),
                Decimal("0"),
                Decimal("0"),
                Decimal("0"),
                Decimal("0"),
                "no_depth",
            )
            return None

        cfg = self._pair_config(exchange, symbol)

        base_order = cfg.order_size_usd if cfg else settings.dynamic_order_usd_min
        order_value = min(
            settings.dynamic_order_usd_max,
            max(base_order, settings.dynamic_order_usd_min),
        )
        clipped_value = book_value * settings.scanner_depth_clip_fraction
        order_value = min(order_value, clipped_value, book_value)
        order_value = max(order_value, settings.dynamic_order_usd_min)
        if order_value <= 0:
            self._log_candidate(
                exchange,
                symbol,
                "RED_X",
                Decimal("0"),
                Decimal("0"),
                book_value,
                Decimal("0"),
                Decimal("0"),
                "order_value",
            )
            return None

        bid_agg = self._aggregate_side(bids, order_value)
        ask_agg = self._aggregate_side(asks, order_value)
        if not bid_agg or not ask_agg:
            self._log_candidate(
                exchange,
                symbol,
                "RED_X",
                Decimal("0"),
                Decimal("0"),
                book_value,
                Decimal("0"),
                Decimal("0"),
                "insufficient_depth",
            )
            return None

        avg_bid, bid_value = bid_agg
        avg_ask, ask_value = ask_agg

        order_value_filled = min(bid_value, ask_value)
        available_depth = book_value

        gross_edge = (avg_ask - avg_bid) / avg_bid * Decimal("10000")

        top_bid_depth = self._total_value(bids[: settings.scanner_max_depth_levels])
        top_ask_depth = self._total_value(asks[: settings.scanner_max_depth_levels])

        maker_fee_bps = Decimal(cfg.maker_fee_bps if cfg else 12)
        taker_fee_bps = Decimal(cfg.taker_fee_bps if cfg else 35)

        market_meta = getattr(client._client, "markets", {}).get(symbol, {})  # type: ignore[attr-defined]
        maker_fee = market_meta.get("maker")
        taker_fee = market_meta.get("taker")
        if maker_fee is not None:
            maker_fee_bps = Decimal(str(maker_fee)) * Decimal("10000")
        if taker_fee is not None:
            taker_fee_bps = Decimal(str(taker_fee)) * Decimal("10000")

        total_fee_bps = maker_fee_bps * Decimal("2")
        buffer_bps = Decimal(cfg.slippage_buffer_bps if cfg else settings.scanner_min_spread_bps)
        slippage_bps = estimate_slippage_bps(order_value_filled, available_depth, settings)
        slippage_total_bps = max(slippage_bps, buffer_bps)
        effective_edge = gross_edge - slippage_total_bps
        net_edge = gross_edge - total_fee_bps - slippage_total_bps
        timestamp = time.time()
        base = market_meta.get("base") or (symbol.split("/")[0] if "/" in symbol else symbol)
        quote = market_meta.get("quote") or (symbol.split("/")[1] if "/" in symbol else "")
        ticker = await self._safe_fetch_ticker(client, symbol)
        volume_usd, volume_known = self._estimate_volume_usd(market_meta, ticker, avg_bid, avg_ask)
        if not volume_known:
            if ticker is None:
                logger.debug("[SCAN] %s %s: ticker fetch returned None, volume unknown", exchange.upper(), symbol)
            else:
                logger.debug("[SCAN] %s %s: ticker fetched but no volume data found (ticker keys: %s)", exchange.upper(), symbol, list(ticker.keys())[:10] if isinstance(ticker, dict) else "N/A")

        floor_bps = self._net_edge_floor(exchange)
        marker = "GREEN_CHECK"
        reason = "ok"
        skip = False
        if net_edge < floor_bps:
            marker = "RED_X"
            reason = f"edge<{floor_bps}"
            skip = True
        elif available_depth < settings.scanner_min_depth_usd:
            marker = "RED_X"
            reason = f"depth<{settings.scanner_min_depth_usd}"
            skip = True
        elif volume_known and volume_usd < settings.scanner_min_volume_usd:
            marker = "RED_X"
            reason = f"volume<{settings.scanner_min_volume_usd}"
            skip = True
        elif not volume_known:
            marker = "WARN"
            reason = "volume_unknown"

        effective_value = min(order_value_filled, available_depth)
        score = net_edge * effective_value

        volume_for_log = volume_usd.quantize(Decimal("0.01")) if volume_known else Decimal("0")

        # Always log the candidate, even if it doesn't meet thresholds
        self._log_candidate(
            exchange,
            symbol,
            marker,
            gross_edge.quantize(Decimal("0.01")),
            net_edge.quantize(Decimal("0.01")),
            available_depth.quantize(Decimal("0.01")),
            volume_for_log,
            score.quantize(Decimal("0.01")),
            reason,
            details=f"slip={slippage_total_bps.quantize(Decimal('0.01'))} fees={total_fee_bps.quantize(Decimal('0.01'))}",
        )

        if skip:
            return None

        return PairSnapshot(
            exchange=exchange,
            symbol=symbol,
            base=base,
            quote=quote,
            spread_bps=gross_edge.quantize(Decimal("0.01")),
            gross_edge_bps=gross_edge.quantize(Decimal("0.01")),
            slippage_bps=slippage_total_bps.quantize(Decimal("0.01")),
            fees_bps=total_fee_bps.quantize(Decimal("0.01")),
            net_edge_bps=net_edge.quantize(Decimal("0.01")),
            effective_edge_bps=effective_edge.quantize(Decimal("0.01")),
            depth_usd=available_depth.quantize(Decimal("0.01")),
            top_bid_depth_usd=top_bid_depth.quantize(Decimal("0.01")),
            top_ask_depth_usd=top_ask_depth.quantize(Decimal("0.01")),
            maker_fee_bps=maker_fee_bps.quantize(Decimal("0.01")),
            taker_fee_bps=taker_fee_bps.quantize(Decimal("0.01")),
            volume_usd=volume_for_log,
            volume_known=volume_known,
             marker=marker,
             reason=reason,
            order_value_usd=order_value_filled.quantize(Decimal("0.01")),
            avg_bid=avg_bid.quantize(Decimal("0.00001")),
            avg_ask=avg_ask.quantize(Decimal("0.00001")),
            score=score.quantize(Decimal("0.01")),
            timestamp=timestamp,
        )

    def _pair_config(self, exchange: str, symbol: str) -> Optional[PairConfig]:
        for cfg in self._config.pairs:
            if cfg.exchange == exchange and cfg.symbol == symbol:
                return cfg
        return None

    async def _safe_fetch_ticker(self, client: RestExchangeClient, symbol: str) -> Optional[Dict[str, Any]]:
        try:
            ticker = await client.fetch_ticker(symbol)
            if not isinstance(ticker, dict):
                logger.debug("[SCAN] ticker fetch returned non-dict for %s %s: %s", client._id.upper(), symbol, type(ticker))
                return None
            # Log if ticker has volume data
            has_volume = any(
                key in ticker or (isinstance(ticker.get("info"), dict) and key in ticker.get("info", {}))
                for key in ["volume", "baseVolume", "quoteVolume", "volumeUsd24h", "volume_usd_24h"]
            )
            if not has_volume:
                logger.debug("[SCAN] ticker for %s %s has no volume fields", client._id.upper(), symbol)
            return ticker
        except Exception as exc:
            logger.warning("[SCAN] ticker fetch failed for %s %s: %s", client._id.upper(), symbol, exc)
            return None

    def _estimate_volume_usd(
        self,
        market: Dict[str, Any],
        ticker: Optional[Dict[str, Any]],
        bid: Decimal,
        ask: Decimal,
    ) -> Tuple[Decimal, bool]:
        def _to_decimal(value: Any) -> Optional[Decimal]:
            if value is None:
                return None
            try:
                dec = Decimal(str(value))
                if dec > 0:
                    return dec
            except Exception:
                return None
            return None

        mid = (bid + ask) / Decimal("2")
        info = market.get("info", {}) if isinstance(market, dict) else {}

        if ticker and isinstance(ticker, dict):
            ticker_info = ticker.get("info", {}) if isinstance(ticker.get("info"), dict) else {}
            keys_usd = [
                "volumeUsd24h",
                "volume_usd_24h",
                "volume_24h_usd",
                "volumeUsd",
                "volumeUsd24Hr",
                "volume_usd",
                "volume24hUsd",
            ]
            for key in keys_usd:
                candidate = _to_decimal(ticker_info.get(key))
                if candidate:
                    return candidate, True

            keys_quote = [
                "quoteVolume",
                "volumeQuote",
                "volume_24h_quote",
                "quoteVolume24h",
            ]
            for key in keys_quote:
                candidate = _to_decimal(ticker.get(key) or ticker_info.get(key))
                if candidate:
                    return candidate, True

            keys_base = [
                "baseVolume",
                "volume",
                "volume_24h",
                "baseVolume24h",
            ]
            for key in keys_base:
                base_candidate = _to_decimal(ticker.get(key) or ticker_info.get(key))
                if base_candidate:
                    return base_candidate * mid, True

        keys_usd_info = [
            "volumeUsd24h",
            "volumeUsd24Hr",
            "volumeUsd",
            "usdVolume",
            "volume_usd_24h",
        ]
        for key in keys_usd_info:
            candidate = _to_decimal(info.get(key))
            if candidate:
                return candidate, True

        base_volume = _to_decimal(info.get("volume") or info.get("baseVolume") or market.get("baseVolume"))
        if base_volume:
            return base_volume * mid, True

        quote_volume = _to_decimal(info.get("quoteVolume") or market.get("quoteVolume"))
        if quote_volume:
            return quote_volume, True

        return Decimal("0"), False


    def _total_value(self, levels: Sequence[Sequence[float]]) -> Decimal:
        total = Decimal("0")
        for raw_price, raw_qty in levels:
            price = Decimal(str(raw_price))
            qty = Decimal(str(raw_qty))
            if price <= 0 or qty <= 0:
                continue
            total += price * qty
        return total

    def _aggregate_side(
        self,
        levels: Sequence[Sequence[float]],
        desired_value: Decimal,
    ) -> Optional[tuple[Decimal, Decimal]]:
        remaining = desired_value
        if remaining <= 0:
            return None
        value_accum = Decimal("0")
        price_times_qty = Decimal("0")
        qty_accum = Decimal("0")
        for raw_price, raw_qty in levels:
            price = Decimal(str(raw_price))
            qty = Decimal(str(raw_qty))
            if price <= 0 or qty <= 0:
                continue
            level_value = price * qty
            take_value = min(level_value, remaining)
            if take_value <= 0:
                continue
            portion = take_value / level_value
            take_qty = qty * portion
            qty_accum += take_qty
            price_times_qty += take_qty * price
            value_accum += take_value
            remaining -= take_value
            if remaining <= 0:
                break
        if value_accum <= 0 or qty_accum <= 0:
            return None
        avg_price = price_times_qty / qty_accum
        return avg_price, value_accum

    def _net_edge_floor(self, exchange: str) -> Decimal:
        settings = self._config.settings
        if exchange.lower().startswith("coinbase"):
            return Decimal(settings.coinbase_min_net_edge_bps)
        return Decimal(settings.scanner_min_net_edge_bps)

    def _log_candidate(
        self,
        exchange: str,
        symbol: str,
        marker: str,
        spread_bps: Decimal,
        net_edge_bps: Decimal,
        depth_usd: Decimal,
        volume_usd: Decimal,
        score: Decimal,
        reason: str,
        *,
        details: Optional[str] = None,
    ) -> None:
        message = (
            "[SCAN:%s] %s %s spread=%sbps net=%sbps depth_usd=%s volume_usd=%s score=%s reason=%s"
            % (
                marker,
                exchange.upper(),
                symbol,
                spread_bps,
                net_edge_bps,
                depth_usd,
                volume_usd,
                score,
                reason,
            )
        )
        if details:
            message = f"{message} detail={details}"
        logger.info(message)


class PairCatalog:
    """Maintains static and dynamically discovered pair configs."""

    def __init__(self, config: ScalperConfig, initial_pairs: Sequence[PairConfig]) -> None:
        self._config = config
        self._static: Dict[str, PairConfig] = {
            self._key(pair.exchange, pair.symbol): pair for pair in initial_pairs
        }
        self._dynamic: Dict[str, PairConfig] = {}

    def _key(self, exchange: str, symbol: str) -> str:
        return f"{exchange}:{symbol}"

    def get(self, exchange: str, symbol: str) -> Optional[PairConfig]:
        key = self._key(exchange, symbol)
        return self._static.get(key) or self._dynamic.get(key)

    def get_by_key(self, key: str) -> Optional[PairConfig]:
        return self._static.get(key) or self._dynamic.get(key)

    def register_dynamic(self, snapshot: PairSnapshot) -> Optional[PairConfig]:
        key = self._key(snapshot.exchange, snapshot.symbol)
        if key in self._static:
            return self._static[key]
        if key in self._dynamic:
            return self._dynamic[key]
        if len(self._dynamic) >= self._config.settings.max_dynamic_pairs:
            return None
        floor = self._net_edge_floor(snapshot.exchange)
        if snapshot.net_edge_bps < floor:
            return None
        if snapshot.depth_usd < self._config.settings.scanner_min_depth_usd:
            return None
        if snapshot.volume_known and snapshot.volume_usd < self._config.settings.scanner_min_volume_usd:
            return None
        cfg = self._build_config(snapshot)
        if cfg is None:
            return None
        self._dynamic[key] = cfg
        logger.info(
            "[DISCOVER] enabling %s %s net_edge=%sbps depth_usd=%s volume_usd=%s",
            snapshot.exchange.upper(),
            snapshot.symbol,
            snapshot.net_edge_bps,
            snapshot.depth_usd,
            snapshot.volume_usd,
        )
        return cfg

    def configs(self) -> Iterable[PairConfig]:
        yield from self._static.values()
        yield from self._dynamic.values()

    def _build_config(self, snapshot: PairSnapshot) -> Optional[PairConfig]:
        settings = self._config.settings
        order_usd = max(snapshot.order_value_usd, settings.dynamic_order_usd_min)
        order_usd = min(order_usd, settings.dynamic_order_usd_max)
        if order_usd < settings.dynamic_order_usd_min:
            return None

        floor = self._net_edge_floor(snapshot.exchange)
        target_edge = max(snapshot.net_edge_bps, floor)
        maker_fee = int(snapshot.maker_fee_bps.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        taker_fee = int(snapshot.taker_fee_bps.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        min_edge = int(max(Decimal(settings.minimum_target_edge_bps), target_edge * Decimal("0.75")))
        probe_edge = int(max(min_edge // 2, settings.minimum_target_edge_bps // 2))
        max_edge = int(target_edge + Decimal("80"))

        return PairConfig(
            exchange=snapshot.exchange,
            symbol=snapshot.symbol,
            base=snapshot.base,
            quote=snapshot.quote,
            order_size_usd=order_usd,
            min_notional_usd=settings.dynamic_order_usd_min,
            target_edge_bps=int(target_edge),
            min_edge_bps=min_edge,
            probe_edge_bps=probe_edge,
            max_edge_bps=max_edge,
            slippage_buffer_bps=8,
            maker_fee_bps=maker_fee,
            taker_fee_bps=taker_fee,
            depth_clip_fraction=settings.scanner_depth_clip_fraction,
            max_spread_bps=400,
            min_spread_bps=settings.scanner_min_spread_bps,
            volatility_floor_bps=30,
            volatility_ceiling_bps=400,
            inventory_pressure_bps=10,
            base_probe_size_usd=settings.dynamic_order_usd_min,
            max_probe_size_usd=settings.dynamic_order_usd_max,
            probe_step_usd=Decimal("1"),
        )

    def _net_edge_floor(self, exchange: str) -> Decimal:
        if exchange.lower().startswith("coinbase"):
            return Decimal(self._config.settings.coinbase_min_net_edge_bps)
        return Decimal(self._config.settings.scanner_min_net_edge_bps)
