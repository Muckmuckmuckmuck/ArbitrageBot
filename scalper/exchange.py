from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, Optional

import ccxt  # type: ignore

logger = logging.getLogger(__name__)


@dataclass
class ExchangeCredentials:
    api_key: str
    api_secret: str
    passphrase: Optional[str] = None


class RestExchangeClient:
    """Thin REST-only wrapper around ccxt clients for Coinbase and Gemini."""

    def __init__(self, venue: str, creds: ExchangeCredentials, *, sandbox: bool = False) -> None:
        if venue not in {"coinbase", "coinbaseadvanced", "gemini"}:
            raise ValueError(f"Unsupported venue {venue}")

        if venue == "coinbase":
            client_cls = ccxt.coinbaseprime
            options = {"hostname": "prime.coinbase.com"}
        elif venue == "coinbaseadvanced":
            client_cls = ccxt.coinbaseadvanced
            options = {}
        else:
            client_cls = ccxt.gemini
            options = {}

        self._client = client_cls({
            "apiKey": creds.api_key,
            "secret": creds.api_secret,
            "password": creds.passphrase,
            "enableRateLimit": True,
            "timeout": 15_000,
            **options,
        })
        if sandbox:
            self._client.set_sandbox_mode(True)

    async def fetch_order_book(self, symbol: str, *, depth: int = 5) -> Dict[str, Any]:
        return await asyncio.to_thread(self._client.fetch_order_book, symbol, depth)

    async def fetch_trades(self, symbol: str, *, limit: int = 50, since: Optional[int] = None) -> Any:
        return await asyncio.to_thread(self._client.fetch_trades, symbol, since, limit)

    async def fetch_balance(self) -> Dict[str, Any]:
        return await asyncio.to_thread(self._client.fetch_balance)

    async def create_limit_order(self, symbol: str, side: str, amount: Decimal, price: Decimal, *, post_only: bool = True) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if post_only:
            params["postOnly"] = True
        return await asyncio.to_thread(
            self._client.create_order,
            symbol,
            "limit",
            side,
            float(amount),
            float(price),
            params,
        )

    async def cancel_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        return await asyncio.to_thread(self._client.cancel_order, order_id, symbol)

    async def fetch_open_orders(self, symbol: Optional[str] = None) -> Any:
        return await asyncio.to_thread(self._client.fetch_open_orders, symbol)

    async def fetch_my_trades(self, symbol: str, *, since: Optional[int] = None, limit: int = 100) -> Any:
        return await asyncio.to_thread(self._client.fetch_my_trades, symbol, since, limit)

    async def close(self) -> None:
        try:
            await asyncio.to_thread(self._client.close)
        except AttributeError:
            pass
