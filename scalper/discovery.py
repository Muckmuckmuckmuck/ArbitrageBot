from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Awaitable, Callable, Dict, List, Optional, Sequence

from .config import PairConfig, ScalperConfig
from .exchange import RestExchangeClient

logger = logging.getLogger(__name__)


@dataclass
class PairSnapshot:
    exchange: str
    symbol: str
    spread_bps: Decimal
    net_edge_bps: Decimal
    depth_usd: Decimal
    maker_fee_bps: Decimal
    taker_fee_bps: Decimal
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

        cfg = self._pair_config(exchange, symbol)
        order_value = cfg.order_size_usd if cfg else Decimal("5")
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
        buffer_bps = Decimal(cfg.slippage_buffer_bps if cfg else 10)
        net_edge = spread - total_fee_bps - buffer_bps - slippage_bps
        timestamp = time.time()
        return PairSnapshot(
            exchange=exchange,
            symbol=symbol,
            spread_bps=spread.quantize(Decimal("0.01")),
            net_edge_bps=net_edge.quantize(Decimal("0.01")),
            depth_usd=depth_usd.quantize(Decimal("0.01")),
            maker_fee_bps=maker_fee_bps.quantize(Decimal("0.01")),
            taker_fee_bps=taker_fee_bps.quantize(Decimal("0.01")),
            timestamp=timestamp,
        )

    def _pair_config(self, exchange: str, symbol: str) -> Optional[PairConfig]:
        for cfg in self._config.pairs:
            if cfg.exchange == exchange and cfg.symbol == symbol:
                return cfg
        return None
