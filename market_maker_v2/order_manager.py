from __future__ import annotations

import asyncio
import logging
import sqlite3
import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Optional

from .config import PathsConfig, StrategyToggles
from .exchange import ExchangeClient, ExchangeError

logger = logging.getLogger(__name__)


@dataclass
class OrderRecord:
    client_order_id: str
    exchange_order_id: Optional[str]
    symbol: str
    side: str
    price: Decimal
    amount: Decimal
    filled: Decimal
    status: str
    created_at: float
    updated_at: float


class OrderStore:
    """Lightweight SQLite-backed order persistence."""

    def __init__(self, paths: PathsConfig) -> None:
        self.paths = paths
        self.paths.ensure_directories()
        self.conn = sqlite3.connect(self.paths.db_path)
        self.conn.row_factory = sqlite3.Row
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                client_order_id TEXT PRIMARY KEY,
                exchange_order_id TEXT,
                symbol TEXT,
                side TEXT,
                price REAL,
                amount REAL,
                filled REAL,
                status TEXT,
                created_at REAL,
                updated_at REAL
            )
            """
        )
        self.conn.commit()

    def upsert(self, record: OrderRecord) -> None:
        self.conn.execute(
            """
            INSERT INTO orders VALUES(?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(client_order_id) DO UPDATE SET
                exchange_order_id=excluded.exchange_order_id,
                price=excluded.price,
                amount=excluded.amount,
                filled=excluded.filled,
                status=excluded.status,
                updated_at=excluded.updated_at
            """,
            (
                record.client_order_id,
                record.exchange_order_id,
                record.symbol,
                record.side,
                float(record.price),
                float(record.amount),
                float(record.filled),
                record.status,
                record.created_at,
                record.updated_at,
            ),
        )
        self.conn.commit()

    def fetch_open(self, symbol: str) -> List[OrderRecord]:
        rows = self.conn.execute(
            "SELECT * FROM orders WHERE symbol=? AND status IN ('open','partially_filled')",
            (symbol,),
        ).fetchall()
        return [self._row_to_record(row) for row in rows]

    def _row_to_record(self, row: sqlite3.Row) -> OrderRecord:
        return OrderRecord(
            client_order_id=row["client_order_id"],
            exchange_order_id=row["exchange_order_id"],
            symbol=row["symbol"],
            side=row["side"],
            price=Decimal(str(row["price"])),
            amount=Decimal(str(row["amount"])),
            filled=Decimal(str(row["filled"])),
            status=row["status"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


class OrderManager:
    """Handles order placement, cancellation, and reconciliation."""

    def __init__(
        self,
        client: ExchangeClient,
        paths: PathsConfig,
        toggles: StrategyToggles,
        maker_fee_bps: Decimal,
        taker_fee_bps: Decimal,
        simulate_mode: bool = False,
    ) -> None:
        self.client = client
        self.store = OrderStore(paths)
        self.toggles = toggles
        self.maker_fee_bps = maker_fee_bps
        self.taker_fee_bps = taker_fee_bps
        self.simulate_mode = simulate_mode
        self._lock = asyncio.Lock()

    async def place_limit_order(
        self,
        symbol: str,
        side: str,
        amount: Decimal,
        price: Decimal,
    ) -> OrderRecord:
        async with self._lock:
            if amount <= 0:
                raise ValueError("amount must be positive")

            created_at = time.time()
            if self.simulate_mode:
                client_order_id = f"sim-{side}-{created_at}"
                record = OrderRecord(
                    client_order_id=client_order_id,
                    exchange_order_id=client_order_id,
                    symbol=symbol,
                    side=side,
                    price=price,
                    amount=amount,
                    filled=Decimal("0"),
                    status="open",
                    created_at=created_at,
                    updated_at=created_at,
                )
                self.store.upsert(record)
                return record

            params = {}
            if self.toggles.enable_post_only:
                params["post_only"] = True
            response = await self.client.create_limit_order(symbol, side, amount, price, params=params)
            record = OrderRecord(
                client_order_id=response.get("clientOrderId") or response.get("id") or f"{side}-{created_at}",
                exchange_order_id=response.get("id"),
                symbol=symbol,
                side=side,
                price=Decimal(str(response.get("price", price))),
                amount=Decimal(str(response.get("amount", amount))),
                filled=Decimal(str(response.get("filled", "0"))),
                status=response.get("status", "open"),
                created_at=created_at,
                updated_at=time.time(),
            )
            self.store.upsert(record)
            return record

    async def cancel_order(self, symbol: str, order: OrderRecord) -> None:
        async with self._lock:
            if self.simulate_mode or not order.exchange_order_id:
                order.status = "cancelled"
                order.updated_at = time.time()
                self.store.upsert(order)
                return
            try:
                await self.client.cancel_order(order.exchange_order_id, symbol)
            except ExchangeError as exc:
                logger.warning("Cancel order failed: %s", exc)
            order.status = "cancelled"
            order.updated_at = time.time()
            self.store.upsert(order)

    async def cancel_all(self, symbol: str) -> None:
        open_orders = self.store.fetch_open(symbol)
        for order in open_orders:
            await self.cancel_order(symbol, order)

    async def reconcile(self, symbol: str) -> List[OrderRecord]:
        """Reconcile stored orders with exchange state."""
        async with self._lock:
            if self.simulate_mode:
                # Nothing to fetch; return current open records
                return self.store.fetch_open(symbol)

            open_orders_resp = await self.client.fetch_open_orders(symbol)
            open_by_id = {order["id"]: order for order in open_orders_resp}
            trades = await self.client.fetch_my_trades(symbol)
            fills_by_order: Dict[str, Decimal] = {}
            for trade in trades:
                order_id = trade.get("order")
                if not order_id:
                    continue
                amount = Decimal(str(trade.get("amount", "0")))
                fills_by_order[order_id] = fills_by_order.get(order_id, Decimal("0")) + amount

            reconciled: List[OrderRecord] = []
            for record in self.store.fetch_open(symbol):
                exchange_payload = None
                if record.exchange_order_id:
                    exchange_payload = open_by_id.get(record.exchange_order_id)
                if exchange_payload:
                    record.price = Decimal(str(exchange_payload.get("price", record.price)))
                    record.amount = Decimal(str(exchange_payload.get("amount", record.amount)))
                    record.filled = Decimal(str(exchange_payload.get("filled", record.filled)))
                    record.status = exchange_payload.get("status", record.status)
                else:
                    filled_amount = fills_by_order.get(record.exchange_order_id or "", record.filled)
                    record.filled = filled_amount
                    record.status = "filled" if filled_amount >= record.amount else "cancelled"
                record.updated_at = time.time()
                self.store.upsert(record)
                reconciled.append(record)
            return reconciled

    def get(self, client_order_id: str) -> Optional[OrderRecord]:
        row = self.store.conn.execute(
            "SELECT * FROM orders WHERE client_order_id=?", (client_order_id,)
        ).fetchone()
        if not row:
            return None
        return self.store._row_to_record(row)

    def mark_filled(self, record: OrderRecord, fill_price: Optional[Decimal] = None) -> OrderRecord:
        record.filled = record.amount
        if fill_price is not None:
            record.price = fill_price
        record.status = "filled"
        record.updated_at = time.time()
        self.store.upsert(record)
        return record

    def mark_partially_filled(self, record: OrderRecord, filled_amount: Decimal, fill_price: Decimal) -> OrderRecord:
        record.filled = filled_amount
        record.price = fill_price
        record.status = "partially_filled"
        record.updated_at = time.time()
        self.store.upsert(record)
        return record

    def fee_for(self, side: str, amount: Decimal, price: Decimal, maker: bool = True) -> Decimal:
        bps = self.maker_fee_bps if maker else self.taker_fee_bps
        return amount * price * (bps / Decimal("10000"))

