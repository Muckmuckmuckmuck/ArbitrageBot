from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Awaitable, Callable, Dict, Iterable, List, Optional, Sequence

from .config import PairConfig, ScalperConfig
from .exchange import RestExchangeClient

logger = logging.getLogger(__name__)


@dataclass
class PairSnapshot:
    exchange: str
    symbol: str
    base: str
    quote: str
    spread_bps: Decimal
    net_edge_bps: Decimal
    depth_usd: Decimal
    maker_fee_bps: Decimal
    taker_fee_bps: Decimal
    volume_usd: Decimal
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
            for venue in exchanges:
                try:
                    client = await self._client_getter(venue)
                except Exception as exc:
                    logger.debug("[SCAN] unable to init client for %s: %s", venue, exc)
                    continue
                markets = getattr(client._client, "markets", {})  # type: ignore[attr-defined]
                if not markets:
                    try:
                        await client.load_markets()
                        markets = getattr(client._client, "markets", {})  # type: ignore[attr-defined]
                    except Exception as exc:  # pragma: no cover - defensive
                        logger.debug("[SCAN] load_markets failed for %s: %s", venue, exc)
                        continue
                candidates = self._select_markets(markets)
                for symbol in candidates:
                    snapshot = await self._evaluate_market(venue, symbol, client)
                    if snapshot:
                        logger.info(
                            "[SCAN:CANDIDATE] %s %s spread=%sbps net=%sbps maker_fee=%sbps taker_fee=%sbps depth_usd=%s volume_usd=%s",
                            venue.upper(),
                            symbol,
                            snapshot.spread_bps,
                            snapshot.net_edge_bps,
                            snapshot.maker_fee_bps,
                            snapshot.taker_fee_bps,
                            snapshot.depth_usd,
                            snapshot.volume_usd,
                        )
                        key = f"{venue}:{symbol}"
                        self._snapshots[key] = snapshot
                        results.append(snapshot)
            # Keep most recent snapshot for any market not refreshed this pass
            results.extend(value for key, value in self._snapshots.items() if value not in results)
            results.sort(key=lambda snap: snap.net_edge_bps, reverse=True)
            return results

    def _select_markets(self, markets: Dict[str, Dict]) -> Sequence[str]:
        allowed_quotes = set(self._config.settings.scanner_quote_currencies)
        filtered = []
        for symbol, meta in markets.items():
            if not meta.get("active", True):
                continue
            quote = meta.get("quote")
            if quote not in allowed_quotes:
                continue
            filtered.append((meta.get("info", {}).get("volume") or meta.get("info", {}).get("baseVolume") or 0, symbol))
        filtered.sort(reverse=True, key=lambda item: float(item[0]) if item[0] is not None else 0.0)
        limit = self._config.settings.scanner_max_markets
        return [symbol for _, symbol in filtered[:limit]]

    async def _evaluate_market(
        self,
        exchange: str,
        symbol: str,
        client: RestExchangeClient,
    ) -> Optional[PairSnapshot]:
        try:
            book = await client.fetch_order_book(symbol, depth=3)
        except Exception as exc:
            logger.debug("[SCAN] order book fetch failed for %s %s: %s", exchange, symbol, exc)
            return None

        bids = book.get("bids") or []
        asks = book.get("asks") or []
        if not bids or not asks:
            return None

        best_bid_price, best_bid_qty = bids[0]
        best_ask_price, best_ask_qty = asks[0]
        bid = Decimal(str(best_bid_price))
        ask = Decimal(str(best_ask_price))
        if bid <= 0 or ask <= 0 or ask <= bid:
            return None

        spread = (ask - bid) / bid * Decimal("10000")
        depth_usd = min(Decimal(str(best_bid_qty)) * bid, Decimal(str(best_ask_qty)) * ask)
        if depth_usd <= 0:
            return None

        settings = self._config.settings
        if depth_usd < settings.scanner_min_depth_usd:
            return None

        cfg = self._pair_config(exchange, symbol)
        base_order = cfg.order_size_usd if cfg else settings.dynamic_order_usd_min
        depth_clip = depth_usd * settings.scanner_depth_clip_fraction
        order_value = min(base_order, depth_clip, depth_usd)
        order_value = max(order_value, settings.dynamic_order_usd_min)
        order_value = min(order_value, settings.dynamic_order_usd_max)

        maker_fee_bps = Decimal(cfg.maker_fee_bps if cfg else 12)
        taker_fee_bps = Decimal(cfg.taker_fee_bps if cfg else 35)

        market_meta = getattr(client._client, "markets", {}).get(symbol, {})  # type: ignore[attr-defined]
        maker_fee = market_meta.get("maker")
        taker_fee = market_meta.get("taker")
        if maker_fee is not None:
            maker_fee_bps = Decimal(str(maker_fee)) * Decimal("10000")
        if taker_fee is not None:
            taker_fee_bps = Decimal(str(taker_fee)) * Decimal("10000")

        slippage_bps = Decimal("0")
        if depth_usd > 0:
            slippage_bps = (order_value / depth_usd) * Decimal("10000") * Decimal("0.5")

        total_fee_bps = maker_fee_bps * Decimal("2")
        buffer_bps = Decimal(cfg.slippage_buffer_bps if cfg else settings.scanner_min_spread_bps)
        net_edge = spread - total_fee_bps - buffer_bps - slippage_bps
        timestamp = time.time()
        base = market_meta.get("base") or (symbol.split("/")[0] if "/" in symbol else symbol)
        quote = market_meta.get("quote") or (symbol.split("/")[1] if "/" in symbol else "")
        ticker = await self._safe_fetch_ticker(client, symbol)
        volume_usd = self._estimate_volume_usd(market_meta, ticker, bid, ask)
        if volume_usd < settings.scanner_min_volume_usd:
            return None

        return PairSnapshot(
            exchange=exchange,
            symbol=symbol,
            base=base,
            quote=quote,
            spread_bps=spread.quantize(Decimal("0.01")),
            net_edge_bps=net_edge.quantize(Decimal("0.01")),
            depth_usd=depth_usd.quantize(Decimal("0.01")),
            maker_fee_bps=maker_fee_bps.quantize(Decimal("0.01")),
            taker_fee_bps=taker_fee_bps.quantize(Decimal("0.01")),
            volume_usd=volume_usd.quantize(Decimal("0.01")),
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
            return ticker if isinstance(ticker, dict) else None
        except Exception as exc:
            logger.debug("[SCAN] ticker fetch failed for %s: %s", symbol, exc)
            return None

    def _estimate_volume_usd(self, market: Dict[str, any], ticker: Optional[Dict[str, Any]], bid: Decimal, ask: Decimal) -> Decimal:
        info = market.get("info", {}) if isinstance(market, dict) else {}
        if ticker:
            ticker_base = ticker.get("baseVolume") or ticker.get("volume")
            ticker_quote = ticker.get("quoteVolume")
            ticker_usd = ticker.get("info", {}).get("volumeUsd24h") if isinstance(ticker.get("info"), dict) else None
            try:
                if ticker_usd is not None:
                    return Decimal(str(ticker_usd))
            except Exception:
                pass
            try:
                if ticker_quote is not None:
                    return Decimal(str(ticker_quote))
            except Exception:
                pass
            try:
                if ticker_base is not None:
                    mid = (bid + ask) / Decimal("2")
                    return Decimal(str(ticker_base)) * mid
            except Exception:
                pass
        for key in ("volumeUsd24h", "volumeUsd24Hr", "volumeUsd", "usdVolume"):
            value = info.get(key)
            if value is not None:
                try:
                    return Decimal(str(value))
                except Exception:
                    continue
        base_volume = info.get("volume") or info.get("baseVolume") or market.get("baseVolume")
        if base_volume is not None:
            try:
                base_volume_dec = Decimal(str(base_volume))
                mid = (bid + ask) / Decimal("2")
                return base_volume_dec * mid
            except Exception:
                pass
        quote_volume = info.get("quoteVolume") or market.get("quoteVolume")
        if quote_volume is not None:
            try:
                return Decimal(str(quote_volume))
            except Exception:
                pass
        return Decimal("0")


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
        if snapshot.net_edge_bps < Decimal(self._config.settings.scanner_min_net_edge_bps):
            return None
        if snapshot.depth_usd < self._config.settings.scanner_min_depth_usd:
            return None
        if snapshot.volume_usd < self._config.settings.scanner_min_volume_usd:
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
        order_usd = snapshot.depth_usd * settings.scanner_depth_clip_fraction
        order_usd = max(order_usd, settings.dynamic_order_usd_min)
        order_usd = min(order_usd, settings.dynamic_order_usd_max)
        if order_usd < settings.dynamic_order_usd_min:
            return None

        target_edge = max(snapshot.net_edge_bps, Decimal(settings.minimum_target_edge_bps))
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
