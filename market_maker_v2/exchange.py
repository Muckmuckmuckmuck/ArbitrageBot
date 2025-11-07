from __future__ import annotations

import asyncio
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, List, Optional

import ccxt  # type: ignore

from .config import ExchangeRuntimeConfig
from .rate_limiter import RateLimitedTask, TokenBucket


class ExchangeError(RuntimeError):
    """Unified exception for exchange faults."""


def _synchronous_exchange_factory(cfg: ExchangeRuntimeConfig) -> ccxt.Exchange:
    kwargs: Dict[str, Any] = {
        "enableRateLimit": True,
    }
    if cfg.api_key and cfg.api_secret:
        kwargs.update(
            {
                "apiKey": cfg.api_key,
                "secret": cfg.api_secret,
            }
        )
    if cfg.passphrase:
        kwargs["password"] = cfg.passphrase
    exchange_cls = getattr(ccxt, cfg.ccxt_id)
    return exchange_cls(kwargs)


class ExchangeClient:
    """Async-friendly wrapper around ccxt exchanges using to_thread."""

    def __init__(self, cfg: ExchangeRuntimeConfig) -> None:
        self.cfg = cfg
        self._exchange = _synchronous_exchange_factory(cfg)
        self._loop = asyncio.get_event_loop()
        self.public_bucket = TokenBucket(
            capacity=max(1.0, cfg.rate_limit_public_rps * 2.0),
            refill_rate_per_sec=cfg.rate_limit_public_rps,
        )
        self.private_bucket = TokenBucket(
            capacity=max(1.0, cfg.rate_limit_private_rps * 2.0),
            refill_rate_per_sec=cfg.rate_limit_private_rps,
        )

    async def _call(self, fn_name: str, *args: Any, private: bool = False, **kwargs: Any) -> Any:
        bucket = self.private_bucket if private else self.public_bucket
        await bucket.consume()
        exchange = self._exchange
        func = getattr(exchange, fn_name)
        try:
            return await asyncio.to_thread(func, *args, **kwargs)
        except ccxt.BaseError as exc:
            raise ExchangeError(str(exc)) from exc

    async def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        return await self._call("fetch_ticker", symbol)

    async def fetch_order_book(self, symbol: str, depth: int = 10) -> Dict[str, Any]:
        return await self._call("fetch_order_book", symbol, depth)

    async def fetch_balance(self) -> Dict[str, Any]:
        return await self._call("fetch_balance", private=True)

    async def create_limit_order(
        self,
        symbol: str,
        side: str,
        amount: Decimal,
        price: Decimal,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        params = params or {}
        return await self._call(
            "create_limit_order",
            symbol,
            side,
            float(amount),
            float(price),
            params,
            private=True,
        )

    async def cancel_order(self, order_id: str, symbol: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        params = params or {}
        return await self._call("cancel_order", order_id, symbol, params, private=True)

    async def fetch_open_orders(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        if symbol:
            return await self._call("fetch_open_orders", symbol, private=True)
        return await self._call("fetch_open_orders", private=True)

    async def fetch_my_trades(self, symbol: Optional[str] = None, since: Optional[int] = None) -> List[Dict[str, Any]]:
        if symbol:
            return await self._call("fetch_my_trades", symbol, since, None, private=True)
        return await self._call("fetch_my_trades", private=True)

    async def close(self) -> None:
        await asyncio.to_thread(self._exchange.close)

