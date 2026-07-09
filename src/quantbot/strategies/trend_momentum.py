"""HIGH-GROWTH sleeve: aggressive risk-managed momentum — built to BEAT SPY.

Blended, optionally vol-normalized momentum (Jegadeesh-Titman; Moskowitz-Ooi-Pedersen;
Antonacci absolute-momentum crash filter). Keep the top-N with positive absolute
momentum (else cash), CONCENTRATE in them (momentum-weighted) so the strongest trends
pull their weight. A loose vol target (in the runner) only de-risks in real turmoil.
Signal horizons, vol-normalization and rebalance cadence are configurable for ablation.
"""
from __future__ import annotations

from typing import Optional

import pandas as pd

from quantbot.strategies import common
from quantbot.strategies.base import Strategy


class TrendMomentum(Strategy):
    name = "trend_momentum"
    sleeve = "high_growth"

    def __init__(
        self,
        lookbacks=(63, 126, 252),
        skip: int = 21,
        top_n: int = 2,
        vol_window: int = 60,
        weighting: str = "momentum",
        vol_normalize: bool = True,
        rebalance: str = "M",
        reversion_weight: float = 0.0,
    ):
        self.lookbacks = lookbacks
        self.skip = skip
        self.top_n = top_n
        self.vol_window = vol_window
        self.weighting = weighting
        self.vol_normalize = vol_normalize
        self.rebalance = rebalance
        self.reversion_weight = reversion_weight

    def target_weights(
        self, prices: pd.DataFrame, regime: Optional[pd.DataFrame] = None,
        volume: Optional[pd.DataFrame] = None,
    ) -> pd.DataFrame:
        px = prices.sort_index()
        sig = common.signal_momentum(px, self.lookbacks, self.skip, self.vol_window,
                                     self.vol_normalize, self.reversion_weight)
        if volume is not None:  # volume confirmation (Kronos-derived): favor moves backed by rising volume
            vt = common.volume_trend(volume).reindex(index=sig.index, columns=sig.columns).fillna(1.0)
            sig = sig * vt
        vol = common.realized_vol(px, self.vol_window)

        def decide(dt: pd.Timestamp) -> pd.Series:
            m = sig.loc[dt].dropna()
            winners = m[m > 0.0].sort_values(ascending=False).head(self.top_n)
            if winners.empty:
                return pd.Series(0.0, index=px.columns)  # dual-momentum: all cash
            w = common.combine_weights(list(winners.index), self.weighting, vol.loc[dt], sig.loc[dt])
            return w * (len(winners) / self.top_n)

        return common.periodic_rebalance(px, decide, self.rebalance)
