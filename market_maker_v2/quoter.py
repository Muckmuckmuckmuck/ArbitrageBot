from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import List, Tuple

from .config import PairConfig


@dataclass
class QuoteDecision:
    bids: List[Tuple[Decimal, Decimal]]
    asks: List[Tuple[Decimal, Decimal]]
    spread_bps: Decimal
    inventory_skew: Decimal


class Quoter:
    """Computes optimal multi-layer quotes and adaptive sizing."""

    def __init__(self, pair_cfg: PairConfig, capital_usd: Decimal) -> None:
        self.cfg = pair_cfg
        self.capital_usd = capital_usd
        self.alpha = Decimal("0.2")
        self.buy_fill_rate = Decimal("0.5")
        self.sell_fill_rate = Decimal("0.5")

    def record_fill(self, side: str, filled: bool) -> None:
        target = Decimal("1") if filled else Decimal("0")
        if side == "buy":
            self.buy_fill_rate = (Decimal("1") - self.alpha) * self.buy_fill_rate + self.alpha * target
        else:
            self.sell_fill_rate = (Decimal("1") - self.alpha) * self.sell_fill_rate + self.alpha * target

    def compute(
        self,
        mid_price: Decimal,
        spread_pct: Decimal,
        volatility: Decimal,
        inventory_skew: Decimal,
        bid_depth_usd: Decimal,
        ask_depth_usd: Decimal,
    ) -> QuoteDecision:
        base_spread = self.cfg.base_spread_bps / Decimal("10000")
        min_spread = self.cfg.min_spread_bps / Decimal("10000")
        max_spread = self.cfg.max_spread_bps / Decimal("10000")

        dynamic_spread = max(base_spread, spread_pct)
        dynamic_spread += abs(volatility) * Decimal("1.2")
        dynamic_spread = max(dynamic_spread, min_spread)
        dynamic_spread = min(dynamic_spread, max_spread)

        layer_spacing = self.cfg.layer_spacing_bps / Decimal("10000")
        spread_half = dynamic_spread / 2

        buy_size_base = self.capital_usd * self.cfg.base_order_size_pct
        sell_size_base = buy_size_base
        buy_size_base = max(buy_size_base, self.cfg.min_order_usd)
        sell_size_base = max(sell_size_base, self.cfg.min_order_usd)

        if bid_depth_usd > Decimal("0"):
            depth_factor = min(Decimal("2.0"), bid_depth_usd / (buy_size_base or Decimal("1")))
            buy_size_base *= depth_factor
        if ask_depth_usd > Decimal("0"):
            depth_factor = min(Decimal("2.0"), ask_depth_usd / (sell_size_base or Decimal("1")))
            sell_size_base *= depth_factor

        buy_size_base *= Decimal("0.6") + self.buy_fill_rate * Decimal("0.8")
        sell_size_base *= Decimal("0.6") + self.sell_fill_rate * Decimal("0.8")

        buy_size_base = min(buy_size_base, self.capital_usd * self.cfg.max_order_size_pct)
        sell_size_base = min(sell_size_base, self.capital_usd * self.cfg.max_order_size_pct)

        bids: List[Tuple[Decimal, Decimal]] = []
        asks: List[Tuple[Decimal, Decimal]] = []

        for layer in range(self.cfg.layers):
            layer_offset = Decimal(layer) * layer_spacing
            skew = inventory_skew * (Decimal("1") + Decimal(layer) * Decimal("0.2"))

            bid_price = mid_price * (Decimal("1") - (spread_half + layer_offset) - skew)
            ask_price = mid_price * (Decimal("1") + (spread_half + layer_offset) - skew)
            bid_price = bid_price.quantize(Decimal("0.01"))
            ask_price = ask_price.quantize(Decimal("0.01"))

            layer_weight = max(Decimal("0.3"), Decimal("1") - Decimal(layer) * Decimal("0.25"))
            bid_amount = (buy_size_base * layer_weight / max(bid_price, Decimal("0.01"))).quantize(Decimal("0.00001"))
            ask_amount = (sell_size_base * layer_weight / max(ask_price, Decimal("0.01"))).quantize(Decimal("0.00001"))

            if bid_amount > Decimal("0"):
                bids.append((bid_price, bid_amount))
            if ask_amount > Decimal("0"):
                asks.append((ask_price, ask_amount))

        return QuoteDecision(
            bids=bids,
            asks=asks,
            spread_bps=dynamic_spread * Decimal("10000"),
            inventory_skew=inventory_skew,
        )

