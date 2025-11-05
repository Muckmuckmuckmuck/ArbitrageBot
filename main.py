#!/usr/bin/env python3
"""
Intra-Exchange Arbitrage Trading Bot
Runs the arbitrage engine using the same simple approach that worked for BTC purchase
"""

import asyncio
from intra_exchange_arbitrage_engine import main

if __name__ == '__main__':
    asyncio.run(main())
