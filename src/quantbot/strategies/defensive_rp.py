"""SAFE-GROWTH sleeve: conservative trend-following — aims to beat a HYSA (~7%).

A HYSA/T-bill is the hurdle, so this holds return-generating assets, not just
Treasuries: it tilts to low-vol equity (USMV — low-vol / betting-against-beta,
Frazzini-Pedersen 2014) plus gold and duration. Each asset is gated by a Faber
(2007) trend filter — held only while above its long SMA, else that asset's target
weight rotates to a T-bill proxy (BIL) — so it sidesteps falling-knife regimes (e.g.
bonds in 2022). `asset_weights` sets the strategic defensive mix (equity-tilted to
clear the HYSA hurdle); trend-gating + vol targeting keep drawdowns contained. It
therefore carries more risk than a HYSA by construction — the price of the return.
"""
from __future__ import annotations

from typing import Dict, List, Optional

import pandas as pd

from quantbot.strategies import common
from quantbot.strategies.base import Strategy


class DefensiveRiskParity(Strategy):
    name = "defensive_rp"
    sleeve = "safe_growth"

    def __init__(
        self,
        risk_symbols: List[str],
        cash_symbol: str,
        trend_window: int = 200,
        vol_window: int = 60,
        weighting: str = "equal",
        asset_weights: Optional[Dict[str, float]] = None,
    ):
        self.risk_symbols = risk_symbols
        self.cash_symbol = cash_symbol
        self.trend_window = trend_window
        self.vol_window = vol_window
        self.weighting = weighting
        self.asset_weights = asset_weights

    def target_weights(
        self, prices: pd.DataFrame, regime: Optional[pd.DataFrame] = None
    ) -> pd.DataFrame:
        px = prices.sort_index()
        risk = [s for s in self.risk_symbols if s in px.columns]
        up = common.trend_up(px, self.trend_window)
        vol = common.realized_vol(px, self.vol_window)
        total_w = sum(self.asset_weights.get(s, 0.0) for s in risk) if self.asset_weights else float(len(risk))

        def decide(dt: pd.Timestamp) -> pd.Series:
            out = pd.Series(0.0, index=px.columns)
            eligible = [s for s in risk if bool(up.loc[dt, s])]  # trend-up only
            if not eligible:
                out[self.cash_symbol] = 1.0
                return out
            if self.asset_weights:  # strategic mix; down-trend assets' share -> cash
                for s in eligible:
                    out[s] = self.asset_weights.get(s, 0.0) / total_w
                out[self.cash_symbol] += 1.0 - out.sum()
            else:
                w = common.combine_weights(eligible, self.weighting, vol.loc[dt], None)
                invested = len(eligible) / len(risk)
                for s in eligible:
                    out[s] = w[s] * invested
                out[self.cash_symbol] += (1.0 - invested)
            return out

        return common.monthly_rebalance(px, decide)
