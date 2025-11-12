from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN
from typing import Optional

from .config import PairConfig
from .market_data import OrderBookSnapshot
from .state import PairRuntimeState

logger = logging.getLogger(__name__)


@dataclass
class QuoteIntent:
    symbol: str
    buy_price: Decimal
    sell_price: Decimal
    buy_size: Decimal
    sell_size: Decimal
    post_buy: bool
    post_sell: bool
    reason: str


class QuotePlanner:
    """Computes limit prices/sizes for a scalping pass."""

    def __init__(self) -> None:
        pass

    def plan(self, cfg: PairConfig, state: PairRuntimeState, snapshot: OrderBookSnapshot, stable_balance: Decimal) -> Optional[QuoteIntent]:
        spread_bps = snapshot.spread_bps
        gross_edge = spread_bps
        fees = Decimal(cfg.maker_fee_bps)
        slip = Decimal(cfg.slippage_buffer_bps)
        net_edge = gross_edge - fees - slip

        if net_edge < 0:
            logger.debug("%s %s net edge negative: %s", cfg.exchange, cfg.symbol, net_edge)
            return None

        target_edge = Decimal(cfg.target_edge_bps)
        if state.last_result == "loss":
            target_edge += Decimal("6")
        if net_edge < target_edge:
            logger.debug("%s %s net edge %s below target %s", cfg.exchange, cfg.symbol, net_edge, target_edge)
            return None

        clip_fraction = Decimal("1") - Decimal(cfg.min_spread_bps) / Decimal("10000")
        buy_price = (snapshot.best_bid * clip_fraction).quantize(Decimal("0.00001"), rounding=ROUND_DOWN)
        sell_price = (snapshot.best_ask * (Decimal("2") - clip_fraction)).quantize(Decimal("0.00001"), rounding=ROUND_DOWN)

        order_value = min(cfg.order_size_usd, stable_balance)
        if order_value < cfg.min_notional_usd:
            logger.debug("%s %s order value %s below min %s", cfg.exchange, cfg.symbol, order_value, cfg.min_notional_usd)
            return None

        buy_size = (order_value / buy_price).quantize(Decimal("0.00001"), rounding=ROUND_DOWN)
        sell_size = (order_value / sell_price).quantize(Decimal("0.00001"), rounding=ROUND_DOWN)

        now = time.time()
        state.last_quote_ts = now

        return QuoteIntent(
            symbol=cfg.symbol,
            buy_price=buy_price,
            sell_price=sell_price,
            buy_size=buy_size,
            sell_size=sell_size,
            post_buy=True,
            post_sell=True,
            reason=f"net_edge={net_edge}bps gross={gross_edge}bps",
        )
