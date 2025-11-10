"""
Dynamic Coinbase market-making engine that relies on the instant-fill OMS.

This wrapper discovers every active Coinbase spot market with at least
$500,000 of 24h quote volume and builds `PairConfig` objects for them. The
core pairs retain hand-tuned overrides, while everything else inherits safe
defaults sized for low-capital operation while still respecting the fee floors.
"""

from __future__ import annotations

import asyncio
import logging
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from coinbase_gemini_exchanges import (
    CoinbaseGeminiExchangeManager,
    EXCHANGE_COINBASE,
)
from database_manager import DatabaseManager
from instant_fill_oms import ExchangeManagerAdapter, InstantFillMarketMaker, PairConfig

logger = logging.getLogger(__name__)

MIN_VOLUME_USD = Decimal("500000")
DEFAULT_ORDER_SIZE_USD = Decimal("3.50")
DEFAULT_MIN_SPREAD_BPS = 280
DEFAULT_PRICE_IMPROVEMENT_BPS = 3
DEFAULT_MAX_QUOTE_INTERVAL_S = 20.0
DEFAULT_FEE_FLOOR_BPS = 200
DEFAULT_MIN_NOTIONAL_USD = Decimal("3.25")
DEFAULT_MIN_DEPTH_USD = Decimal("2500")
ALLOWED_QUOTES = {"USD", "USDC"}

PAIR_OVERRIDES: Dict[str, Dict[str, object]] = {
    "BTC/USD": {
        "order_size_usd": Decimal("4.50"),
        "min_spread_bps": 230,
        "price_improve_bps": 2,
        "min_depth_usd": Decimal("3500"),
        "target_edge_bps": 300,
    },
    "BTC/USDC": {
        "order_size_usd": Decimal("4.50"),
        "min_spread_bps": 230,
        "price_improve_bps": 2,
        "min_depth_usd": Decimal("3500"),
        "target_edge_bps": 300,
    },
    "ETH/USD": {
        "order_size_usd": Decimal("4.00"),
        "min_spread_bps": 240,
        "price_improve_bps": 2,
        "min_depth_usd": Decimal("3200"),
        "target_edge_bps": 310,
    },
    "ETH/USDC": {
        "order_size_usd": Decimal("4.00"),
        "min_spread_bps": 240,
        "price_improve_bps": 2,
        "min_depth_usd": Decimal("3200"),
        "target_edge_bps": 310,
    },
    "SOL/USD": {
        "order_size_usd": Decimal("3.50"),
        "min_spread_bps": 270,
        "price_improve_bps": 3,
        "min_depth_usd": Decimal("2800"),
        "target_edge_bps": 330,
    },
    "SOL/USDC": {
        "order_size_usd": Decimal("3.50"),
        "min_spread_bps": 270,
        "price_improve_bps": 3,
        "min_depth_usd": Decimal("2800"),
        "target_edge_bps": 330,
    },
}


def _market_is_spot(market: Dict) -> bool:
    if not market:
        return False
    if not market.get("active", True):
        return False
    if market.get("future") or market.get("swap"):
        return False
    if ":" in str(market.get("symbol", "")):
        return False
    return True


def _extract_quote_volume_usd(symbol: str, ticker: Dict) -> Optional[Decimal]:
    if not ticker:
        return None

    for key in ("quoteVolume", "quote_volume"):
        volume_val = ticker.get(key)
        if volume_val:
            try:
                return Decimal(str(volume_val))
            except Exception:  # pragma: no cover - defensive
                logger.debug("[CONFIG] Unable to parse %s %s as Decimal", symbol, key)
                break

    base_volume = ticker.get("baseVolume") or ticker.get("volume")
    last_price = ticker.get("last") or ticker.get("close")
    if base_volume and last_price:
        try:
            return Decimal(str(base_volume)) * Decimal(str(last_price))
        except Exception:  # pragma: no cover - defensive
            logger.debug(
                "[CONFIG] Failed fallback volume computation for %s", symbol
            )
    info = ticker.get("info") or {}
    for key in ("volumeUsd", "volume_usd", "quoteVolumeUsd"):
        if key in info:
            try:
                return Decimal(str(info[key]))
            except Exception:  # pragma: no cover - defensive
                logger.debug("[CONFIG] Unable to parse %s info[%s]", symbol, key)
    return None


def _resolve_decimal(value: object, default: Decimal) -> Decimal:
    if value is None:
        return default
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except Exception:  # pragma: no cover - defensive
        logger.debug("[CONFIG] Falling back to default decimal %s", default)
        return default


def _make_pair_config(symbol: str, override: Dict[str, object]) -> PairConfig:
    order_size = _resolve_decimal(
        override.get("order_size_usd"), DEFAULT_ORDER_SIZE_USD
    )
    min_notional = _resolve_decimal(
        override.get("min_notional_usd"), DEFAULT_MIN_NOTIONAL_USD
    )
    min_depth = _resolve_decimal(
        override.get("min_depth_usd"), DEFAULT_MIN_DEPTH_USD
    )
    min_spread_bps = int(override.get("min_spread_bps", DEFAULT_MIN_SPREAD_BPS))
    price_improve_bps = int(
        override.get("price_improve_bps", DEFAULT_PRICE_IMPROVEMENT_BPS)
    )
    max_quote_interval = float(
        override.get("max_quote_interval_s", DEFAULT_MAX_QUOTE_INTERVAL_S)
    )
    fee_floor_bps = int(override.get("fee_floor_bps", DEFAULT_FEE_FLOOR_BPS))
    target_edge_bps = int(override.get("target_edge_bps", min_spread_bps + 60))

    return PairConfig(
        EXCHANGE_COINBASE,
        symbol,
        order_size_usd=order_size,
        min_spread_bps=min_spread_bps,
        max_quote_interval_s=max_quote_interval,
        min_depth_usd=min_depth,
        min_notional_usd=min_notional,
        price_improve_bps=price_improve_bps,
        fee_floor_bps=fee_floor_bps,
        min_volume_usd=MIN_VOLUME_USD,
        target_edge_bps=target_edge_bps,
    )


async def _coinbase_pair_configs(
    exchange_manager: CoinbaseGeminiExchangeManager,
) -> List[PairConfig]:
    exchange = exchange_manager.get_exchange(EXCHANGE_COINBASE)
    markets = getattr(exchange, "markets", {}) or {}

    candidates: List[str] = []
    for symbol, market in markets.items():
        if not _market_is_spot(market):
            continue
        quote = str(market.get("quote", "")).upper()
        if quote not in ALLOWED_QUOTES:
            continue
        candidates.append(symbol)

    discovered: List[Tuple[str, Decimal, PairConfig]] = []
    for symbol in sorted(candidates):
        try:
            ticker = await exchange_manager.fetch_ticker(EXCHANGE_COINBASE, symbol)
        except Exception as exc:  # pragma: no cover - best effort
            logger.info(
                "[CONFIG] Skipping %s fetch_ticker error: %s",
                symbol,
                exc,
            )
            continue

        volume = _extract_quote_volume_usd(symbol, ticker)
        if volume is None:
            logger.debug(
                "[CONFIG] Skipping %s: unable to determine 24h volume", symbol
            )
            continue
        if volume < MIN_VOLUME_USD:
            logger.debug(
                "[CONFIG] Skipping %s: volume %s < %s",
                symbol,
                volume,
                MIN_VOLUME_USD,
            )
            continue

        override = PAIR_OVERRIDES.get(symbol, {})
        cfg = _make_pair_config(symbol, override)
        discovered.append((symbol, volume, cfg))

    discovered.sort(key=lambda item: item[1], reverse=True)

    if not discovered:
        logger.warning(
            "[CONFIG] No Coinbase markets met the %s volume filter; falling back to core overrides",
            MIN_VOLUME_USD,
        )
        fallback: List[PairConfig] = []
        for symbol, override in PAIR_OVERRIDES.items():
            if symbol not in markets:
                continue
            fallback.append(_make_pair_config(symbol, override))
        if fallback:
            return fallback
        raise RuntimeError(
            "No Coinbase markets satisfied the volume filter and no fallback pairs were available."
        )

    logger.info(
        "[CONFIG] Coinbase high-volume markets selected: %d (threshold=%s)",
        len(discovered),
        MIN_VOLUME_USD,
    )
    for symbol, volume, _ in discovered[:40]:
        logger.info("[CONFIG]   - %s volume≈%s", symbol, volume)
    if len(discovered) > 40:
        logger.info(
            "[CONFIG]   ... %d additional markets omitted from log",
            len(discovered) - 40,
        )

    return [cfg for _, _, cfg in discovered]


class CoinbaseMarketMakingEngine:
    """Thin wrapper that runs the instant-fill market maker for Coinbase pairs."""

    def __init__(
        self,
        exchange_manager: CoinbaseGeminiExchangeManager,
        db_manager: DatabaseManager,
        pair_configs: Optional[List[PairConfig]] = None,
    ) -> None:
        self._exchange_manager = exchange_manager
        self._db_manager = db_manager
        self._adapter = ExchangeManagerAdapter(exchange_manager)
        self._provided_configs = pair_configs
        self._maker: Optional[InstantFillMarketMaker] = None
        self._task: Optional[asyncio.Task] = None
        self._maker_lock = asyncio.Lock()

    async def start(self) -> None:
        await self._ensure_maker()
        if self._maker is None:  # pragma: no cover - defensive
            raise RuntimeError("InstantFillMarketMaker failed to initialize")
        await self._maker.start()
        if self._task is None:
            self._task = asyncio.create_task(self._run_forever())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        if self._maker:
            await self._maker.stop()
            self._maker = None

    async def _ensure_maker(self) -> None:
        if self._maker:
            return
        async with self._maker_lock:
            if self._maker:
                return
            configs = self._provided_configs
            if configs is None:
                configs = await _coinbase_pair_configs(self._exchange_manager)
            if not configs:
                raise RuntimeError("No Coinbase pair configs available")
            self._maker = InstantFillMarketMaker(
                self._adapter,
                self._db_manager,
                configs,
            )

    async def _run_forever(self) -> None:
        try:
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass

