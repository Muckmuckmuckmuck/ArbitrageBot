#!/usr/bin/env python3
"""
Entry-point script for the new modular market-making system.
"""

import argparse
import asyncio
import logging
import sys
from decimal import Decimal

from coinbase_gemini_exchanges import CoinbaseGeminiExchangeManager
from database_manager import DatabaseManager
from instant_fill_oms import (
    ExchangeManagerAdapter,
    InstantFillMarketMaker,
    PairConfig,
)


def configure_logging(level: str, logfile: str | None = None) -> None:
    handlers = [logging.StreamHandler(sys.stdout)]
    if logfile:
        handlers.append(logging.FileHandler(logfile))
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=handlers,
    )


def _default_pair_configs() -> list[PairConfig]:
    return [
        # Coinbase pairs
        PairConfig("coinbase", "BTC/USD", Decimal("3.00"), min_spread_bps=25),
        PairConfig("coinbase", "ETH/USD", Decimal("2.50"), min_spread_bps=30),
        PairConfig("coinbase", "SOL/USD", Decimal("2.00"), min_spread_bps=35),
        PairConfig("coinbase", "AVAX/USD", Decimal("1.50"), min_spread_bps=40),
        PairConfig("coinbase", "LINK/USD", Decimal("1.50"), min_spread_bps=40),
        # Gemini pairs
        PairConfig("gemini", "BTC/USD", Decimal("2.50"), min_spread_bps=35),
        PairConfig("gemini", "ETH/USD", Decimal("2.00"), min_spread_bps=40),
        PairConfig("gemini", "SOL/USD", Decimal("1.50"), min_spread_bps=45),
    ]


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run instant fill market maker")
    parser.add_argument("--log-level", default="INFO")
    parser.add_argument("--log-file", default=None)
    args = parser.parse_args()

    configure_logging(args.log_level, args.log_file)

    exchange_manager = CoinbaseGeminiExchangeManager()
    await exchange_manager.initialize()

    db_manager = DatabaseManager()
    adapter = ExchangeManagerAdapter(exchange_manager)

    pair_configs = _default_pair_configs()
    market_maker = InstantFillMarketMaker(adapter, db_manager, pair_configs)

    try:
        await market_maker.start()
        logging.info("Instant-fill market maker started")
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logging.info("Received keyboard interrupt, shutting down.")
    finally:
        await market_maker.stop()
        await exchange_manager.close()


if __name__ == "__main__":
    asyncio.run(main())

