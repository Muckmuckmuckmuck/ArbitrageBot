#!/usr/bin/env python3
"""
Simplified Gemini market making engine built on top of the instant-fill OMS.
"""

from __future__ import annotations

import asyncio
from decimal import Decimal
import logging
from typing import List, Optional

from coinbase_gemini_exchanges import CoinbaseGeminiExchangeManager
from database_manager import DatabaseManager
from instant_fill_oms import ExchangeManagerAdapter, InstantFillMarketMaker, PairConfig


def _gemini_pair_configs() -> List[PairConfig]:
    configs = [
        PairConfig(
            "gemini",
            "BTC/USD",
            Decimal("25.00"),
            min_spread_bps=110,
            max_quote_interval_s=20.0,
            price_improve_bps=2,
            min_notional_usd=Decimal("15.00"),
            fee_floor_bps=100,
        ),
        PairConfig(
            "gemini",
            "ETH/USD",
            Decimal("18.00"),
            min_spread_bps=125,
            max_quote_interval_s=20.0,
            price_improve_bps=2,
            min_notional_usd=Decimal("12.00"),
            fee_floor_bps=115,
        ),
        PairConfig(
            "gemini",
            "SOL/USD",
            Decimal("15.00"),
            min_spread_bps=140,
            max_quote_interval_s=20.0,
            price_improve_bps=2,
            min_notional_usd=Decimal("10.00"),
            fee_floor_bps=125,
        ),
        PairConfig(
            "gemini",
            "LINK/USD",
            Decimal("12.00"),
            min_spread_bps=150,
            max_quote_interval_s=20.0,
            price_improve_bps=2,
            min_notional_usd=Decimal("10.00"),
            fee_floor_bps=135,
        ),
    ]
    for cfg in configs:
        logging.getLogger(__name__).info(
            "[CONFIG] Gemini pair %s size_usd=%s min_spread_bps=%s quote_interval=%s",
            cfg.symbol,
            cfg.order_size_usd,
            cfg.min_spread_bps,
            cfg.max_quote_interval_s,
        )
    return configs


class GeminiMarketMakingEngine:
    """Thin wrapper that runs the instant-fill market maker for Gemini pairs."""

    def __init__(
        self,
        exchange_manager: CoinbaseGeminiExchangeManager,
        db_manager: DatabaseManager,
        pair_configs: Optional[List[PairConfig]] = None,
    ) -> None:
        adapter = ExchangeManagerAdapter(exchange_manager)
        configs = pair_configs or _gemini_pair_configs()
        logging.getLogger(__name__).info(
            "[INIT] GeminiMarketMakingEngine pairs=%s",
            [cfg.symbol for cfg in configs],
        )
        self._maker = InstantFillMarketMaker(adapter, db_manager, configs)
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
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
        await self._maker.stop()

    async def _run_forever(self) -> None:
        try:
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass

