"""
market_maker_v2
================

Ground-up market-making framework built around a modular architecture.

Modules
-------
config
    Dataclasses for runtime configuration.
exchange
    Thin asynchronous wrapper around ccxt exchanges.
market_data
    Market data polling with health checks and volatility tracking.
order_manager
    Order lifecycle management and reconciliation.
quoter
    Dynamic spread and sizing logic.
inventory
    Inventory tracking, risk checks, and skew calculations.
rate_limiter
    Token bucket implementation and rate-limited task queue.
bot
    High-level orchestrator tying every component together.
"""

from .config import BotConfig, ExchangeRuntimeConfig

__all__ = [
    "BotConfig",
    "ExchangeRuntimeConfig",
]

