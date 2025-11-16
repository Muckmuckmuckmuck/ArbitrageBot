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

        # Use ALL available balance when it's less than configured order size
        # If we have $10 and token is $30, we buy 1/3 token using all $10
        available_capital = stable_balance
        depth_cap = depth_usd * cfg.depth_clip_fraction
        # Cap to both available balance AND depth, but prioritize using all available balance
        base_cap = min(available_capital, depth_cap)
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

        # Calculate tier sizes, but always respect available balance first
        # If available_capital < order_size_usd, use all available capital for fractional tokens
        # Example: $10 balance, $30 token = buy 0.33 tokens using all $10
        premium_size = min(available_capital, cfg.order_size_usd * settings.tier_premium_size_mult)
        standard_size = min(available_capital, cfg.order_size_usd * settings.tier_standard_size_mult)
        probe_size = min(available_capital, settings.tier_probe_size_usd, state.probe_size_usd if state.probe_size_usd > 0 else settings.tier_probe_size_usd)
        
        # When balance is limited, prioritize using all available capital
        # This allows trading fractional tokens (e.g., 0.33 BTC when you have $10 and BTC is $30)
        if available_capital < cfg.order_size_usd:
            # Use all available capital (capped by depth) for limited balance scenarios
            premium_size = min(available_capital, base_cap)
            standard_size = min(available_capital, base_cap)
            probe_size = min(available_capital, base_cap)
        
        tiers = [
            (
                "premium",
                Decimal(settings.tier_premium_edge_bps),
                min(base_cap, premium_size),
            ),
            (
                "standard",
                Decimal(settings.tier_standard_edge_bps),
                min(base_cap, standard_size),
            ),
            (
                "probe",
                Decimal(settings.tier_probe_edge_bps),
                min(base_cap, probe_size),
            ),
        ]

        selected_tier: Optional[str] = None
        selected_value: Optional[Decimal] = None
        effective_edge = net_edge = None
        slippage_bps = None

        for tier_name, threshold, candidate in tiers:
            if candidate is None or candidate <= 0:
                continue
            # Ensure we never exceed available balance
            candidate = min(candidate, available_capital, base_cap)
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

        # Final order value: use selected value but ensure we don't exceed available balance
        # This handles the case where token price > available balance (e.g., $10 balance, $30 token = buy 1/3 token)
        # When balance is limited, use ALL available capital for fractional tokens
        if available_capital < cfg.order_size_usd and selected_tier:
            # For limited balance, try to use all available capital (capped by depth)
            # This allows trading fractional tokens (e.g., 0.33 tokens when you have $10 and token is $30)
            full_capital_value = min(available_capital, base_cap)
            # Re-evaluate edge with full capital to ensure requirements still hold
            eval_result = evaluate(full_capital_value)
            if eval_result:
                eff_edge_full, net_edge_full = eval_result
                # Get the tier threshold that was selected
                tier_threshold = Decimal(settings.tier_probe_edge_bps)
                if selected_tier == "premium":
                    tier_threshold = Decimal(settings.tier_premium_edge_bps)
                elif selected_tier == "standard":
                    tier_threshold = Decimal(settings.tier_standard_edge_bps)
                # Only use full capital if edge requirements still hold
                meets_tier = net_edge_full >= tier_threshold
                if selected_tier != "probe":
                    meets_tier = meets_tier and net_edge_full >= Decimal(settings.minimum_target_edge_bps)
                if meets_tier and eff_edge_full >= min_profit_bps:
                    # Edge requirements hold, use full capital for fractional tokens
                    order_value = full_capital_value
                else:
                    # Edge requirements don't hold with full capital, use selected value
                    order_value = min(selected_value, available_capital)
            else:
                order_value = min(selected_value, available_capital)
        else:
            order_value = min(selected_value, available_capital)
        
        # If balance is very low, use probe size
        if stable_balance < cfg.min_notional_usd * Decimal("1.5"):
            order_value = min(order_value, settings.tier_probe_size_usd, available_capital)

        # Calculate token amounts: if we have $10 and token is $30, we get 0.333 tokens
        # This handles fractional tokens - exchanges support partial token amounts
        buy_size = (order_value / buy_price).quantize(Decimal("0.00001"), rounding=ROUND_DOWN)
        sell_size = (order_value / sell_price).quantize(Decimal("0.00001"), rounding=ROUND_DOWN)
        
        # Ensure we're using as much of available balance as possible (within precision limits)
        # This is especially important for fractional tokens when balance is limited
        if buy_size > 0 and (buy_size * buy_price) < available_capital * Decimal("0.95"):
            # If we're using less than 95% of available balance, try to use more
            max_buy_size = (available_capital / buy_price).quantize(Decimal("0.00001"), rounding=ROUND_DOWN)
            if max_buy_size > buy_size:
                buy_size = max_buy_size
                order_value = buy_size * buy_price
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
