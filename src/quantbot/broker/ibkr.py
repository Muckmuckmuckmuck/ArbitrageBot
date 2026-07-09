"""Live IBKR adapter via ib_async (the maintained ib_insync successor).

Connects to a running IB Gateway / TWS (headless via IBC on the VM). `ib_async` is
imported lazily so the rest of the package (and SimBroker tests) work without it
installed. Sizing in the daily loop uses the shared close panel, not IBKR market
data, so this needs no real-time data subscription — only account + order access.
"""
from __future__ import annotations

from typing import Dict, Optional

from quantbot.broker.base import Broker, Order
from quantbot.config import IBKRConfig


class IBKRBroker(Broker):
    def __init__(self, cfg: Optional[IBKRConfig] = None, order_type: str = "MKT"):
        self._cfg = cfg or IBKRConfig()
        self._order_type = order_type
        self._ib = None  # ib_async.IB, created on connect

    def connect(self) -> None:
        from ib_async import IB  # lazy import

        self._ib = IB()
        self._ib.connect(
            self._cfg.host, self._cfg.port, clientId=self._cfg.client_id, readonly=self._cfg.readonly
        )
        # Paper accounts default to delayed data; harmless for account/order calls.
        try:
            self._ib.reqMarketDataType(3)  # delayed
        except Exception:
            pass

    def disconnect(self) -> None:
        if self._ib is not None and self._ib.isConnected():
            self._ib.disconnect()

    def net_liquidation(self) -> float:
        for v in self._ib.accountValues():
            if v.tag == "NetLiquidation" and v.currency in ("USD", "BASE"):
                return float(v.value)
        raise RuntimeError("NetLiquidation not found in IBKR account values")

    def positions(self) -> Dict[str, float]:
        out: Dict[str, float] = {}
        for p in self._ib.positions():
            if getattr(p.contract, "secType", "STK") == "STK":
                out[p.contract.symbol] = out.get(p.contract.symbol, 0.0) + float(p.position)
        return out

    def price(self, symbol: str) -> float:
        from ib_async import Stock

        contract = Stock(symbol, "SMART", "USD")
        self._ib.qualifyContracts(contract)
        ticker = self._ib.reqMktData(contract, "", False, False)
        self._ib.sleep(1.5)
        px = ticker.marketPrice()
        if px != px:  # NaN
            px = ticker.close or ticker.last or 0.0
        return float(px) if px == px else 0.0

    def submit(self, order: Order) -> Order:
        from ib_async import LimitOrder, MarketOrder, Stock

        if self._cfg.readonly:
            order.status = "blocked"
            order.note = "IBKR readonly"
            return order
        contract = Stock(order.symbol, "SMART", "USD")
        self._ib.qualifyContracts(contract)
        if self._order_type == "LMT":
            limit = order.est_price * (1.002 if order.side == "BUY" else 0.998)
            ib_order = LimitOrder(order.side, order.shares, round(limit, 2))
        else:
            ib_order = MarketOrder(order.side, order.shares)
        trade = self._ib.placeOrder(contract, ib_order)
        self._ib.sleep(1)
        order.status = str(trade.orderStatus.status)
        return order
