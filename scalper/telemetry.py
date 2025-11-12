from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

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

    def skip(self, exchange: str, symbol: str, reason: str) -> None:
        logger.info(
            "[SKIP] %s %s reason=%s",
            exchange.upper(),
            symbol,
            reason,
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

    def cooldown(self, exchange: str, symbol: str, until: float, reason: str) -> None:
        remaining = max(0.0, until - time.time())
        logger.info(
            "[COOLDOWN] %s %s %.1fs reason=%s",
            exchange.upper(),
            symbol,
            remaining,
            reason,
        )
