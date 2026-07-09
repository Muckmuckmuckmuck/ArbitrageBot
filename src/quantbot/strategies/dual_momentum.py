"""MID-GROWTH sleeve: trend-filtered broad-equity with bond fallback (~SPY-lite).

Aims a bit under the index: capture most of equity's upside, dodge the deep bears.
Holds every broad-equity name with positive absolute momentum (up to top_n, so it
stays broadly invested rather than concentrating), equal-weighted; any name with
negative absolute momentum rotates to BONDS (Antonacci) — which cushions sell-offs.
De-fragilized vs vanilla single-asset GEM.
"""
from __future__ import annotations

from typing import List, Optional

import pandas as pd

from quantbot.strategies import common
from quantbot.strategies.base import Strategy


class DualMomentum(Strategy):
    name = "dual_momentum"
    sleeve = "mid_growth"

    def __init__(
        self,
        equity_symbols: List[str],
        bond_symbol: str,
        lookback: int = 252,
        skip: int = 21,
        top_n: int = 4,
        vol_window: int = 60,
        weighting: str = "equal",
    ):
        self.equity_symbols = equity_symbols
        self.bond_symbol = bond_symbol
        self.lookback = lookback
        self.skip = skip
        self.top_n = top_n
        self.vol_window = vol_window
        self.weighting = weighting

    def target_weights(
        self, prices: pd.DataFrame, regime: Optional[pd.DataFrame] = None
    ) -> pd.DataFrame:
        px = prices.sort_index()
        eq = [s for s in self.equity_symbols if s in px.columns]
        mom = common.momentum(px, self.lookback, self.skip)
        vol = common.realized_vol(px, self.vol_window)

        def decide(dt: pd.Timestamp) -> pd.Series:
            out = pd.Series(0.0, index=px.columns)
            m = mom.loc[dt, eq].dropna().sort_values(ascending=False).head(self.top_n)
            pos = list(m[m > 0.0].index)  # absolute momentum > 0
            if not pos:
                out[self.bond_symbol] = 1.0  # risk-off -> bonds
                return out
            w = common.combine_weights(pos, self.weighting, vol.loc[dt], mom.loc[dt])
            fill = len(pos) / self.top_n
            for s in pos:
                out[s] = w[s] * fill
            out[self.bond_symbol] += (1.0 - fill)  # empty slots -> bonds
            return out

        return common.monthly_rebalance(px, decide)
