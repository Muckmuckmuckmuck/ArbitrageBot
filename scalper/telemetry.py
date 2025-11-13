from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional, Sequence

from .persistence import PersistentLogger
from .discovery import PairSnapshot

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
    order_value: Decimal
    expected_profit_usd: Decimal
    reason: str


class Telemetry:
    def __init__(self, persist: Optional[PersistentLogger] = None) -> None:
        self._persist = persist or PersistentLogger()

    def plan(self, payload: PlanTelemetry) -> None:
        logger.info(
            "[PLAN] %s %s buy=%s@%s sell=%s@%s size_usd=%s net_edge=%sbps expected_profit=%s %s",
            payload.exchange.upper(),
            payload.symbol,
            payload.buy_size,
            payload.buy_price,
            payload.sell_size,
            payload.sell_price,
            payload.order_value,
            payload.net_edge_bps,
            payload.expected_profit_usd,
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
                "order_value": str(payload.order_value),
                "expected_profit_usd": str(payload.expected_profit_usd),
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

    def scan(
        self,
        snapshots: Sequence[PairSnapshot],
        *,
        limit: Optional[int] = None,
        floor_bps: Decimal = Decimal("0"),
    ) -> None:
        if not snapshots:
            logger.info("[SCAN] No markets met base criteria this interval")
            self._persist.write("scan", [])
            return
        payload = []
        iterable = snapshots if limit is None else snapshots[:limit]
        for snapshot in iterable:
            marker = "GREEN_CHECK" if snapshot.net_edge_bps >= floor_bps else "RED_X"
            logger.info(
                "[SCAN:%s] %s %s spread=%sbps net=%sbps maker_fee=%sbps taker_fee=%sbps depth_usd=%s order_value=%s volume_usd=%s score=%s",
                marker,
                snapshot.exchange.upper(),
                snapshot.symbol,
                snapshot.spread_bps,
                snapshot.net_edge_bps,
                snapshot.maker_fee_bps,
                snapshot.taker_fee_bps,
                snapshot.depth_usd,
                snapshot.order_value_usd,
                snapshot.volume_usd,
                snapshot.score,
            )
            payload.append(
                {
                    "exchange": snapshot.exchange,
                    "symbol": snapshot.symbol,
                    "spread_bps": str(snapshot.spread_bps),
                    "net_edge_bps": str(snapshot.net_edge_bps),
                    "marker": marker,
                    "maker_fee_bps": str(snapshot.maker_fee_bps),
                    "taker_fee_bps": str(snapshot.taker_fee_bps),
                    "depth_usd": str(snapshot.depth_usd),
                    "order_value_usd": str(snapshot.order_value_usd),
                    "volume_usd": str(snapshot.volume_usd),
                    "score": str(snapshot.score),
                }
            )
        self._persist.write("scan", payload)
