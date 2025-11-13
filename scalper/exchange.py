from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from decimal import Decimal
import threading
import time
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
        normalized = venue.lower()
        if normalized in {"coinbase", "coinbaseadvanced", "coinbaseprime"}:
            client_cls = getattr(ccxt, "coinbase", None)
            if client_cls is None:
                raise AttributeError("ccxt does not provide a coinbase client in this build")
            options = {}
        elif normalized == "gemini":
            client_cls = ccxt.gemini
            options = {}
        else:
            raise ValueError(f"Unsupported venue {venue}")

        self._client = client_cls({
            "apiKey": creds.api_key,
            "secret": creds.api_secret,
            "password": creds.passphrase,
            "enableRateLimit": True,
            "timeout": 15_000,
            **options,
        })
        self._order_lock = asyncio.Lock()
        self._nonce_lock: Optional[threading.Lock] = None
        self._nonce_value: Optional[int] = None

        if sandbox:
            self._client.set_sandbox_mode(True)
        if normalized == "gemini":
            self._client.options = self._client.options or {}
            self._client.options.setdefault("nonce", "milliseconds")
            self._client.options.setdefault("defaultType", "spot")
            self._client.options.setdefault("defaultMarket", "spot")
            self._nonce_lock = threading.Lock()
            self._nonce_value = int(time.time() * 1000)
            self._client.nonce = self._next_nonce  # type: ignore[attr-defined]
        self._id = getattr(self._client, "id", normalized)

    async def fetch_order_book(self, symbol: str, *, depth: int = 5) -> Dict[str, Any]:
        return await asyncio.to_thread(self._client.fetch_order_book, symbol, depth)

    async def fetch_trades(self, symbol: str, *, limit: int = 50, since: Optional[int] = None) -> Any:
        return await asyncio.to_thread(self._client.fetch_trades, symbol, since, limit)

    async def fetch_balance(self) -> Dict[str, Any]:
        return await asyncio.to_thread(self._client.fetch_balance)

    async def fetch_ticker(self, symbol: str) -> Any:
        return await asyncio.to_thread(self._client.fetch_ticker, symbol)

    async def create_limit_order(self, symbol: str, side: str, amount: Decimal, price: Decimal, *, post_only: bool = True) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if post_only:
            params["postOnly"] = True
        if self._id == "gemini":
            params.setdefault("type", "exchange limit")
        async with self._order_lock:
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
        async with self._order_lock:
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

    async def load_markets(self) -> None:
        await asyncio.to_thread(self._client.load_markets)

    def amount_to_precision(self, symbol: str, amount: Decimal) -> Decimal:
        try:
            value = self._client.amount_to_precision(symbol, float(amount))
            return Decimal(str(value))
        except Exception:
            return amount

    def price_to_precision(self, symbol: str, price: Decimal) -> Decimal:
        try:
            value = self._client.price_to_precision(symbol, float(price))
            return Decimal(str(value))
        except Exception:
            return price

    def min_amount(self, symbol: str) -> Optional[Decimal]:
        try:
            market = self._client.market(symbol)
            min_value = market.get("limits", {}).get("amount", {}).get("min")
            return Decimal(str(min_value)) if min_value else None
        except Exception:
            return None

    def _next_nonce(self) -> int:
        if self._nonce_lock is None or self._nonce_value is None:
            return int(time.time() * 1000)
        with self._nonce_lock:
            now = int(time.time() * 1000)
            if now <= self._nonce_value:
                self._nonce_value += 1
            else:
                self._nonce_value = now
            return self._nonce_value
