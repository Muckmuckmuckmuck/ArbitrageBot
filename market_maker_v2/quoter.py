from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Tuple

from .config import PairConfig


@dataclass
class QuoteDecision:
    bid_price: Decimal
    bid_amount: Decimal
    ask_price: Decimal
    ask_amount: Decimal
    spread_bps: Decimal
    inventory_skew: Decimal


class Quoter:
    """Computes optimal bid/ask quotes based on market data & inventory."""

    def __init__(self, pair_cfg: PairConfig, capital_usd: Decimal) -> None:
        self.cfg = pair_cfg
        self.capital_usd = capital_usd

    def compute(
        self,
        mid_price: Decimal,
        spread_pct: Decimal,
        volatility: Decimal,
        inventory_skew: Decimal,
    ) -> QuoteDecision:
        """
        Calculate quote prices and sizes. Spread inputs are expressed as decimals (0.0025 == 0.25%).
        """
        base_spread = self.cfg.base_spread_bps / Decimal("10000")
        min_spread = self.cfg.min_spread_bps / Decimal("10000")
        max_spread = self.cfg.max_spread_bps / Decimal("10000")

        dynamic_spread = max(base_spread, spread_pct)
        dynamic_spread += abs(volatility) * Decimal("1.2")
        dynamic_spread = max(dynamic_spread, min_spread)
        dynamic_spread = min(dynamic_spread, max_spread)

        skew_adjustment = inventory_skew * dynamic_spread

        bid_price = mid_price * (Decimal("1") - (dynamic_spread / 2) - skew_adjustment)
        ask_price = mid_price * (Decimal("1") + (dynamic_spread / 2) - skew_adjustment)

        bid_price = bid_price.quantize(Decimal("0.01"))
        ask_price = ask_price.quantize(Decimal("0.01"))

        per_side_cap = self.capital_usd * Decimal("0.08")  # 8% per side by default
        per_side_cap = max(per_side_cap, self.cfg.min_order_usd)
        bid_amount = (per_side_cap / bid_price).quantize(Decimal("0.00001"))
        ask_amount = (per_side_cap / ask_price).quantize(Decimal("0.00001"))

        return QuoteDecision(
            bid_price=bid_price,
            bid_amount=bid_amount,
            ask_price=ask_price,
            ask_amount=ask_amount,
            spread_bps=dynamic_spread * Decimal("10000"),
            inventory_skew=inventory_skew,
        )

