#!/usr/bin/env python3
"""
Simplified Gemini market making engine built on top of the instant-fill OMS.
"""

from __future__ import annotations

import asyncio
from decimal import Decimal
from typing import List, Optional

from coinbase_gemini_exchanges import CoinbaseGeminiExchangeManager
from database_manager import DatabaseManager
from instant_fill_oms import ExchangeManagerAdapter, InstantFillMarketMaker, PairConfig


def _gemini_pair_configs() -> List[PairConfig]:
    return [
        PairConfig(
            "gemini",
            "BTC/USD",
            Decimal("5.00"),
            min_spread_bps=18,
            max_quote_interval_s=20.0,
        ),
        PairConfig(
            "gemini",
            "ETH/USD",
            Decimal("4.00"),
            min_spread_bps=22,
            max_quote_interval_s=20.0,
        ),
        PairConfig(
            "gemini",
            "SOL/USD",
            Decimal("3.00"),
            min_spread_bps=28,
            max_quote_interval_s=20.0,
        ),
        PairConfig(
            "gemini",
            "LINK/USD",
            Decimal("3.00"),
            min_spread_bps=30,
            max_quote_interval_s=20.0,
        ),
    ]


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

