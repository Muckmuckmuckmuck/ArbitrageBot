"""Global tactical rotation (trend-following across asset classes).

Hold the top-K assets by blended (optionally vol-normalized) momentum that are ALSO
in an uptrend (Faber filter); everything else sits in cash. The universe spans
equities, bonds, gold and commodities, so the engine rotates INTO whatever trends —
when stocks fall it moves to bonds / gold / commodities and can earn in downturns,
long-only. Signal horizons, vol-normalization and cadence are configurable (ablation).

Evidence: Faber (2007) tactical asset allocation; Antonacci dual momentum; Hurst,
Ooi & Pedersen (2017) "A Century of Evidence on Trend-Following Investing".
"""
from __future__ import annotations

from typing import List, Optional

import pandas as pd

from quantbot.strategies import common
from quantbot.strategies.base import Strategy


class GlobalRotation(Strategy):
    name = "global_rotation"
    sleeve = "rotation"

    def __init__(
        self,
        symbols: List[str],
        cash_symbol: str,
        top_n: int = 3,
        lookbacks=(63, 126, 252),
        skip: int = 21,
        trend_window: int = 200,
        vol_window: int = 60,
        weighting: str = "momentum",
        vol_normalize: bool = True,
        rebalance: str = "M",
    ):
        self.symbols = symbols
        self.cash_symbol = cash_symbol
        self.top_n = top_n
        self.lookbacks = lookbacks
        self.skip = skip
        self.trend_window = trend_window
        self.vol_window = vol_window
        self.weighting = weighting
        self.vol_normalize = vol_normalize
        self.rebalance = rebalance

    def target_weights(
        self, prices: pd.DataFrame, regime: Optional[pd.DataFrame] = None
    ) -> pd.DataFrame:
        px = prices.sort_index()
        assets = [s for s in self.symbols if s in px.columns]
        sig = common.signal_momentum(px, self.lookbacks, self.skip, self.vol_window, self.vol_normalize)
        up = common.trend_up(px, self.trend_window)
        vol = common.realized_vol(px, self.vol_window)

        def decide(dt: pd.Timestamp) -> pd.Series:
            out = pd.Series(0.0, index=px.columns)
            m = sig.loc[dt, assets].dropna()
            cand = [s for s in m.index if m[s] > 0.0 and bool(up.loc[dt, s])]
            cand = sorted(cand, key=lambda s: m[s], reverse=True)[: self.top_n]
            if not cand:
                out[self.cash_symbol] = 1.0
                return out
            w = common.combine_weights(cand, self.weighting, vol.loc[dt], sig.loc[dt])
            invested = len(cand) / self.top_n
            for s in cand:
                out[s] = w[s] * invested
            out[self.cash_symbol] += (1.0 - invested)
            return out

        return common.periodic_rebalance(px, decide, self.rebalance)
