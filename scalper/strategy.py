from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN
from typing import Optional, Tuple

from .config import PairConfig, EngineSettings
from .market_data import OrderBookSnapshot
from .state import PairRuntimeState
from .edge_utils import estimate_slippage_bps

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
        if not snapshot.bids or not snapshot.asks:
            state.record_skip("no_depth")
            return None

        spread_bps = snapshot.spread_bps
        if spread_bps <= 0:
            state.record_skip("no_spread")
            return None

        gross_edge = spread_bps
        maker_fee_bps = Decimal(cfg.maker_fee_bps)
        total_fee_bps = maker_fee_bps * Decimal("2")
        min_profit_bps = Decimal(settings.tier_min_profit_bps)
        depth_usd = snapshot.depth_usd
        if depth_usd <= 0:
            state.record_skip("no_depth")
            return None

        balance_cap = min(cfg.order_size_usd, stable_balance)
        depth_cap = depth_usd * cfg.depth_clip_fraction
        base_cap = min(balance_cap, depth_cap)
        if base_cap <= 0:
            state.record_skip("no_depth")
            return None

        def evaluate(order_value: Decimal) -> Optional[Tuple[Decimal, Decimal]]:
            if order_value <= 0:
                return None
            slippage = estimate_slippage_bps(order_value, depth_usd, settings)
            effective_edge = gross_edge - slippage
            net_edge_local = effective_edge - total_fee_bps
            return effective_edge, net_edge_local

        tiers = [
            (
                "premium",
                Decimal(settings.tier_premium_edge_bps),
                min(base_cap, cfg.order_size_usd * settings.tier_premium_size_mult),
            ),
            (
                "standard",
                Decimal(settings.tier_standard_edge_bps),
                min(base_cap, cfg.order_size_usd * settings.tier_standard_size_mult),
            ),
            (
                "probe",
                Decimal(settings.tier_probe_edge_bps),
                min(base_cap, settings.tier_probe_size_usd, state.probe_size_usd),
            ),
        ]

        selected_tier: Optional[str] = None
        selected_value: Optional[Decimal] = None
        effective_edge = net_edge = None
        slippage_bps = None

        for tier_name, threshold, candidate in tiers:
            if candidate is None or candidate <= 0:
                continue
            candidate = min(candidate, base_cap, stable_balance)
            if candidate < cfg.min_notional_usd:
                continue
            eval_result = evaluate(candidate)
            if not eval_result:
                continue
            eff_edge, net_edge_local = eval_result
            meets_floor = net_edge_local >= threshold
            if tier_name != "probe":
                meets_floor = meets_floor and net_edge_local >= Decimal(settings.minimum_target_edge_bps)
            if not meets_floor:
                continue
            if eff_edge < min_profit_bps:
                continue
            selected_tier = tier_name
            selected_value = candidate
            effective_edge = eff_edge
            net_edge = net_edge_local
            slippage_bps = estimate_slippage_bps(candidate, depth_usd, settings)
            break

        if not selected_tier or selected_value is None or effective_edge is None or net_edge is None or slippage_bps is None:
            state.record_skip("tier_floor")
            return None

        logger.debug(
            "[PLAN_TRACE] %s %s tier=%s spread=%sbps fees=%sbps slip=%sbps eff=%sbps net=%sbps",
            cfg.exchange.upper(),
            cfg.symbol,
            selected_tier,
            gross_edge.quantize(Decimal("0.01")),
            total_fee_bps.quantize(Decimal("0.01")),
            slippage_bps.quantize(Decimal("0.01")),
            effective_edge.quantize(Decimal("0.01")),
            net_edge.quantize(Decimal("0.01")),
        )
        state.recent_net_edges.append(net_edge)
        state.last_edge_bps = net_edge
        state.tier_scores[selected_tier] = net_edge
        state.current_tier = selected_tier

        buy_price = snapshot.best_bid
        sell_price = snapshot.best_ask

        available_adjust = net_edge - min_profit_bps
        if available_adjust > 0:
            buy_adjust = min(available_adjust / Decimal("2"), Decimal(settings.max_bid_improve_bps))
            sell_adjust = min(available_adjust - buy_adjust, Decimal(settings.max_sell_reduce_bps))
            if buy_adjust > 0:
                buy_price *= (Decimal("1") + buy_adjust / Decimal("10000"))
            if sell_adjust > 0:
                sell_price *= (Decimal("1") - sell_adjust / Decimal("10000"))

        if state.inventory:
            inv_pressure = Decimal(cfg.inventory_pressure_bps) / Decimal("10000")
            if inv_pressure > 0:
                buy_price *= (Decimal("1") - inv_pressure)
                sell_price *= (Decimal("1") - inv_pressure * Decimal("0.6"))

        buy_price = buy_price.quantize(Decimal("0.00001"), rounding=ROUND_DOWN)
        sell_price = sell_price.quantize(Decimal("0.00001"), rounding=ROUND_DOWN)
        if sell_price <= buy_price:
            sell_price = (buy_price * Decimal("1.0003")).quantize(Decimal("0.00001"), rounding=ROUND_DOWN)

        order_value = selected_value
        if stable_balance < cfg.min_notional_usd * Decimal("1.5"):
            order_value = min(order_value, settings.tier_probe_size_usd)

        buy_size = (order_value / buy_price).quantize(Decimal("0.00001"), rounding=ROUND_DOWN)
        sell_size = (order_value / sell_price).quantize(Decimal("0.00001"), rounding=ROUND_DOWN)

        if buy_size <= 0 or sell_size <= 0:
            state.record_skip("size_zero")
            return None

        state.last_quote_ts = time.time()
        state.last_quote_reason = (
            f"tier={selected_tier} net={net_edge.quantize(Decimal('0.01'))}bps "
            f"slip={slippage_bps.quantize(Decimal('0.01'))}bps val={order_value.quantize(Decimal('0.01'))}"
        )

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
