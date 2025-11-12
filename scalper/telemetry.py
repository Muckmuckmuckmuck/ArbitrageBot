from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from .persistence import PersistentLogger

logger = logging.getLogger(__name__)


@dataclass
class PlanTelemetry:
    exchange: str
    symbol: str
    buy_size: Decimal
    buy_price: Decimal
    sell_size: Decimal
    sell_price: Decimal
    net_edge_bps: Decimal
    reason: str


class Telemetry:
    def __init__(self, persist: Optional[PersistentLogger] = None) -> None:
        self._persist = persist or PersistentLogger()

    def plan(self, payload: PlanTelemetry) -> None:
        logger.info(
            "[PLAN] %s %s buy=%s@%s sell=%s@%s net_edge=%sbps %s",
            payload.exchange.upper(),
            payload.symbol,
            payload.buy_size,
            payload.buy_price,
            payload.sell_size,
            payload.sell_price,
            payload.net_edge_bps,
            payload.reason,
        )
        self._persist.write(
            "plan",
            {
                "exchange": payload.exchange,
                "symbol": payload.symbol,
                "buy_size": str(payload.buy_size),
                "buy_price": str(payload.buy_price),
                "sell_size": str(payload.sell_size),
                "sell_price": str(payload.sell_price),
                "net_edge_bps": str(payload.net_edge_bps),
                "reason": payload.reason,
            },
        )

    def skip(self, exchange: str, symbol: str, reason: str) -> None:
        logger.info(
            "[SKIP] %s %s reason=%s",
            exchange.upper(),
            symbol,
            reason,
        )
        self._persist.write(
            "skip",
            {
                "exchange": exchange,
                "symbol": symbol,
                "reason": reason,
            },
        )

    def edge(self, exchange: str, symbol: str, gross_bps: Decimal, net_bps: Decimal, target_bps: Decimal) -> None:
        logger.debug(
            "[EDGE] %s %s gross=%sbps net=%sbps target=%sbps",
            exchange.upper(),
            symbol,
            gross_bps,
            net_bps,
            target_bps,
        )
        self._persist.write(
            "edge",
            {
                "exchange": exchange,
                "symbol": symbol,
                "gross_bps": str(gross_bps),
                "net_bps": str(net_bps),
                "target_bps": str(target_bps),
            },
        )

    def cooldown(self, exchange: str, symbol: str, until: float, reason: str) -> None:
        remaining = max(0.0, until - time.time())
        logger.info(
            "[COOLDOWN] %s %s %.1fs reason=%s",
            exchange.upper(),
            symbol,
            remaining,
            reason,
        )
        self._persist.write(
            "cooldown",
            {
                "exchange": exchange,
                "symbol": symbol,
                "remaining": remaining,
                "reason": reason,
            },
        )
