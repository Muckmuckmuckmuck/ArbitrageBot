from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN
from typing import Optional

from .config import PairConfig, EngineSettings
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
    order_value: Decimal
    reason: str


class QuotePlanner:
    """Computes limit prices/sizes for a scalping pass."""

    def __init__(self) -> None:
        pass

    def plan(
        self,
        cfg: PairConfig,
        state: PairRuntimeState,
        snapshot: OrderBookSnapshot,
        stable_balance: Decimal,
        settings: EngineSettings,
    ) -> Optional[QuoteIntent]:
        spread_bps = snapshot.spread_bps
        if spread_bps <= 0:
            state.record_skip("no_spread")
            return None

        gross_edge = spread_bps
        maker_fee = Decimal(cfg.maker_fee_bps)
        maker_total = maker_fee if maker_fee >= Decimal("40") else maker_fee * Decimal("2")
        slip = Decimal(cfg.slippage_buffer_bps)
        net_edge = gross_edge - maker_total - slip
        logger.debug(
            "[PLAN_TRACE] %s %s spread=%sbps maker_total=%sbps slip=%sbps net=%sbps",
            cfg.exchange.upper(),
            cfg.symbol,
            gross_edge.quantize(Decimal("0.01")),
            maker_total.quantize(Decimal("0.01")),
            slip.quantize(Decimal("0.01")),
            net_edge.quantize(Decimal("0.01")),
        )
        state.recent_net_edges.append(net_edge)
        state.last_edge_bps = net_edge

        global_floor = Decimal(settings.minimum_target_edge_bps)
        if net_edge < max(Decimal(cfg.min_edge_bps), global_floor):
            state.record_skip("edge_floor")
            return None

        target_edge = max(Decimal(cfg.target_edge_bps), global_floor)
        if state.last_result == "loss":
            target_edge = min(Decimal(cfg.max_edge_bps), target_edge + Decimal("8"))
        elif state.last_result == "win" and state.win_streak > 1:
            target_edge = max(target_edge, Decimal(cfg.target_edge_bps) + Decimal("5"))

        if net_edge < target_edge:
            state.record_skip("edge_target")
            return None

        depth_bid_usd = snapshot.bid_depth * snapshot.best_bid
        depth_ask_usd = snapshot.ask_depth * snapshot.best_ask
        if depth_bid_usd <= 0 or depth_ask_usd <= 0:
            state.record_skip("no_depth")
            return None
        depth_usd = min(depth_bid_usd, depth_ask_usd)

        clip_reduction_bps = (
            settings.fast_fill_clip_bps
            if state.last_latency_ms and state.last_latency_ms < settings.fast_fill_latency_ms
            else settings.slow_fill_clip_bps
        )
        clip_fraction = Decimal("1") - Decimal(cfg.min_spread_bps + clip_reduction_bps) / Decimal("10000")
        clip_fraction = max(Decimal("0.98"), min(Decimal("1.0"), clip_fraction))

        buy_price = (snapshot.best_bid * clip_fraction).quantize(Decimal("0.00001"), rounding=ROUND_DOWN)
        max_sell_clip = Decimal("1") + Decimal(cfg.min_spread_bps + clip_reduction_bps) / Decimal("10000")
        sell_price = (snapshot.best_ask * max_sell_clip).quantize(Decimal("0.00001"), rounding=ROUND_DOWN)

        order_value = min(cfg.order_size_usd, stable_balance)
        depth_cap = depth_usd * cfg.depth_clip_fraction
        order_value = min(order_value, depth_cap)
        if stable_balance < cfg.min_notional_usd * Decimal("2"):
            order_value = min(order_value, Decimal("3"))

        if order_value < cfg.min_notional_usd:
            state.record_skip("notional")
            return None

        probe_size = state.probe_size_usd if net_edge < Decimal(cfg.target_edge_bps) else order_value
        order_value = min(order_value, probe_size)

        if state.inventory:
            # inventory skew: tighten sell, widen buy
            inv_pressure = Decimal(cfg.inventory_pressure_bps) / Decimal("10000")
            buy_price = (buy_price * (Decimal("1") - inv_pressure)).quantize(Decimal("0.00001"), rounding=ROUND_DOWN)
            sell_price = (sell_price * (Decimal("1") - inv_pressure * Decimal("0.6"))).quantize(Decimal("0.00001"), rounding=ROUND_DOWN)

        buy_size = (order_value / buy_price).quantize(Decimal("0.00001"), rounding=ROUND_DOWN)
        sell_size = (order_value / sell_price).quantize(Decimal("0.00001"), rounding=ROUND_DOWN)

        if buy_size <= 0 or sell_size <= 0:
            state.record_skip("size_zero")
            return None

        state.last_quote_ts = time.time()
        state.last_quote_reason = f"net_edge={net_edge.quantize(Decimal('0.01'))}bps target={target_edge}bps"

        return QuoteIntent(
            symbol=cfg.symbol,
            buy_price=buy_price,
            sell_price=sell_price,
            buy_size=buy_size,
            sell_size=sell_size,
            post_buy=True,
            post_sell=True,
            order_value=order_value,
            reason=state.last_quote_reason,
        )
