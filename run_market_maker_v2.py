#!/usr/bin/env python3
"""
Entry-point script for the new modular market-making system.
"""

import argparse
import asyncio
import logging
import sys

from market_maker_v2 import BotConfig
from market_maker_v2.bot import MarketMakerBot


def configure_logging(level: str, logfile: str | None = None) -> None:
    handlers = [logging.StreamHandler(sys.stdout)]
    if logfile:
        handlers.append(logging.FileHandler(logfile))
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=handlers,
    )


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run market_maker_v2")
    parser.add_argument("--config", help="Path to config module or file (optional)")
    parser.add_argument("--log-level", default="INFO")
    parser.add_argument("--log-file", default=None)
    args = parser.parse_args()

    configure_logging(args.log_level, args.log_file)

    config = BotConfig.default()
    bot = MarketMakerBot(config)

    try:
        await bot.start()
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logging.info("Received keyboard interrupt, shutting down.")
    finally:
        await bot.stop()


if __name__ == "__main__":
    asyncio.run(main())

